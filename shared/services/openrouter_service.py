import json

from loguru import logger

from shared.config.config_model import ConfigModel
from shared.services.http_client import HTTPClient


class OpenRouterService:
    def __init__(
        self,
        client: HTTPClient,
        api_key: str,
        model: str,
        items: list[dict],
        prompt: str,
        config: ConfigModel,
    ) -> None:
        self.client = client
        self.ak = api_key
        self.mod = model
        self.items = items
        self.pr = prompt
        self.cfg = config

    async def get_response(self, text: str) -> dict:
        logger.info("Extracting info from AI")
        try:
            response: dict = await self.client.post_json(
                self.ak, self.mod, text, self.pr
            )
            output = response.get("output", [])
            if not output:
                raise ValueError("Empty output")
            content = output[0].get("content", [])
            if not content:
                raise ValueError("Empty content")
            text = content[0].get("text")
            if not text:
                raise ValueError("Empty text")

            logger.success("Successfully extracted content from AI")

            # Сначала пробуем как есть
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.bind(
                    error_position=e.pos,
                    error_line=e.lineno,
                    error_col=e.colno,
                    text_preview=text[:500]
                ).warning("Failed to parse AI response, attempting fixes")
                
                # Попытка 1: Убрать переносы строк
                text_fixed = text.replace('\n', ' ').replace('\r', ' ')
                try:
                    return json.loads(text_fixed)
                except json.JSONDecodeError:
                    pass
                
                # Попытка 2: Заменить одинарные кавычки на двойные
                text_fixed = text.replace("'", '"')
                try:
                    return json.loads(text_fixed)
                except json.JSONDecodeError:
                    pass
                
                # Попытка 3: Обе исправления вместе
                text_fixed = text.replace('\n', ' ').replace('\r', ' ').replace("'", '"')
                try:
                    return json.loads(text_fixed)
                except json.JSONDecodeError:
                    logger.bind(text_sample=text[:1000]).error(
                        "All JSON fix attempts failed, returning empty list"
                    )
                    return []
                    
        except Exception as exc:
            logger.bind(error=exc.__class__.__name__).exception(
                "Failed to extract info from AI"
            )
            raise

    async def batch_response(self):
        all_results = []
        total_batches = (len(self.items) + self.cfg.ai.batch_count - 1) // self.cfg.ai.batch_count
        
        logger.bind(
            total_items=len(self.items),
            batch_size=self.cfg.ai.batch_count,
            total_batches=total_batches
        ).info("Starting batch AI processing")

        for batch_idx in range(0, len(self.items), self.cfg.ai.batch_count):
            batch_num = batch_idx // self.cfg.ai.batch_count + 1
            batch_items = self.items[batch_idx : batch_idx + self.cfg.ai.batch_count]
            
            ref_field_name = self.cfg.database.model_dump().get(self.cfg.ai.ref_field, self.cfg.database.title)
            
            query_list = [
                {
                    "id": batch_idx + local_idx,
                    "text": item.get(ref_field_name, item.get(self.cfg.database.title, "")),
                    "sku": item.get(self.cfg.database.sku, ""),
                }
                for local_idx, item in enumerate(batch_items)
            ]
            
            try:
                query_str = str(query_list)
                logger.bind(
                    batch=f"{batch_num}/{total_batches}",
                    items_in_batch=len(query_list)
                ).info("Processing batch")
                
                batch_results = await self.get_response(query_str)
                
                if isinstance(batch_results, list):
                    if batch_results:
                        all_results.extend(batch_results)
                        logger.bind(
                            batch=f"{batch_num}/{total_batches}",
                            results_count=len(batch_results)
                        ).success("Batch processed successfully")
                    else:
                        logger.bind(
                            batch=f"{batch_num}/{total_batches}"
                        ).warning("Batch returned empty results")
                else:
                    all_results.append(batch_results)
                    logger.bind(
                        batch=f"{batch_num}/{total_batches}",
                        results_count=1
                    ).success("Batch processed successfully")
                
            except Exception as exc:
                logger.bind(
                    batch=f"{batch_num}/{total_batches}",
                    error=exc.__class__.__name__,
                    batch_start_idx=batch_idx
                ).error("Failed to process batch, skipping")

        logger.bind(total_results=len(all_results)).info("Batch processing completed")
        return all_results
