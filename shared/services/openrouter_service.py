import json
from typing import Any

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

    async def get_response(self, text: str) -> dict | None:
        logger.info("Extracting info from AI")
        try:
            response: dict = await self.client.post_json(
                self.ak, self.mod, text, self.pr, self.cfg.ai.second_model
            )
            choices: list[dict[str, Any]] = response.get("choices", [{}])
            msg = choices[0].get("message", {}).get("content", "")
            if not msg:
                logger.error("Empty message in AI response")
                return None

            logger.success("Successfully extracted content from AI")

            try:
                return json.loads(msg)
            except json.JSONDecodeError as e:
                logger.bind(
                    error_position=e.pos,
                    error_line=e.lineno,
                    error_col=e.colno,
                    text_preview=msg[:500],
                ).warning("Failed to parse AI response, attempting fixes")

                msg_fixed = msg.replace("\n", " ").replace("\r", " ")
                try:
                    return json.loads(msg_fixed)
                except json.JSONDecodeError:
                    pass

                msg_fixed = msg.replace("'", '"')
                try:
                    return json.loads(msg_fixed)
                except json.JSONDecodeError:
                    pass

                msg_fixed = (
                    msg.replace("\n", " ").replace("\r", " ").replace("'", '"')
                )
                try:
                    return json.loads(msg_fixed)
                except json.JSONDecodeError:
                    logger.bind(text_sample=msg[:1000]).error(
                        "All JSON fix attempts failed"
                    )
                    return None

        except Exception as exc:
            logger.bind(error=exc.__class__.__name__).exception(
                "Failed to extract info from AI"
            )
            return None

    async def batch_response(self):
        all_results = []
        failed_skus = []  # SKU записей, которые не удалось обработать

        total_batches = (
            len(self.items) + self.cfg.ai.batch_count - 1
        ) // self.cfg.ai.batch_count

        logger.bind(
            total_items=len(self.items),
            batch_size=self.cfg.ai.batch_count,
            total_batches=total_batches,
        ).info("Starting batch AI processing")

        for batch_idx in range(0, len(self.items), self.cfg.ai.batch_count):
            batch_num = batch_idx // self.cfg.ai.batch_count + 1
            batch_items = self.items[
                batch_idx : batch_idx + self.cfg.ai.batch_count
            ]

            ref_field_name = getattr(
                self.cfg.database,
                self.cfg.ai.ref_field,
                self.cfg.database.title,
            )

            if batch_num == 1:
                logger.bind(
                    batch=f"{batch_num}/{total_batches}",
                    ref_field_name=ref_field_name,
                    ref_field_config=self.cfg.ai.ref_field,
                    database_id=self.cfg.database.id,
                    database_sku=self.cfg.database.sku,
                    database_title=self.cfg.database.title,
                    sample_item_keys=(
                        list(batch_items[0].keys())[:15] if batch_items else []
                    ),
                ).info("Batch processing configuration")

            query_list = []
            batch_id_to_sku = {}

            for local_idx, item in enumerate(batch_items):
                item_id = item.get(self.cfg.database.id, "")
                sku = item.get(self.cfg.database.sku, "")

                if batch_num == 1 and local_idx == 0:
                    logger.bind(
                        batch=f"{batch_num}/{total_batches}",
                        item_id=item_id,
                        sku=sku,
                        item_keys=list(item.keys())[:20],
                    ).info("First item in batch details")

                if not item_id or not sku:
                    if batch_num == 1 and local_idx < 3:
                        logger.bind(
                            batch=f"{batch_num}/{total_batches}",
                            item_idx=local_idx,
                            item_id=item_id,
                            sku=sku,
                            has_item_id=bool(item_id),
                            has_sku=bool(sku),
                        ).warning("Skipping item due to missing id or sku")
                    continue

                ref_text = item.get(ref_field_name, "")
                if not ref_text:
                    logger.bind(
                        batch=f"{batch_num}/{total_batches}",
                        item_id=item_id,
                        sku=sku,
                        ref_field_name=ref_field_name,
                        available_keys=list(item.keys())[:10],
                    ).warning("Item missing ref_field text")

                query_list.append(
                    {
                        "id": item_id,
                        "text": ref_text
                        or item.get(self.cfg.database.title, ""),
                    }
                )

                if sku:
                    batch_id_to_sku[item_id] = sku

            try:
                if not query_list:
                    logger.bind(
                        batch=f"{batch_num}/{total_batches}",
                        batch_items_count=len(batch_items),
                        ref_field_name=ref_field_name,
                    ).warning("Query list is empty, skipping batch")
                    continue

                query_str = json.dumps(query_list, ensure_ascii=False)
                logger.bind(
                    batch=f"{batch_num}/{total_batches}",
                    items_in_batch=len(query_list),
                    query_preview=query_str[:200] if query_str else "",
                ).info("Processing batch")

                batch_results = await self.get_response(query_str)

                if batch_results is None:
                    failed_skus.extend(batch_id_to_sku.values())
                    logger.bind(
                        batch=f"{batch_num}/{total_batches}",
                        failed_items=len(batch_id_to_sku),
                    ).error(
                        "Batch processing failed, marking all items as failed"
                    )
                    continue

                if isinstance(batch_results, list):
                    if batch_results:
                        returned_ids = set()
                        for result in batch_results:
                            if isinstance(result, dict) and "id" in result:
                                returned_ids.add(result["id"])

                        for item_id, sku in batch_id_to_sku.items():
                            if item_id not in returned_ids:
                                failed_skus.append(sku)
                                logger.bind(
                                    batch=f"{batch_num}/{total_batches}",
                                    sku=sku,
                                    item_id=item_id,
                                ).warning("Item not returned in AI response")

                        all_results.extend(batch_results)
                        logger.bind(
                            batch=f"{batch_num}/{total_batches}",
                            results_count=len(batch_results),
                            expected_count=len(query_list),
                        ).success("Batch processed successfully")
                    else:
                        failed_skus.extend(batch_id_to_sku.values())
                        logger.bind(
                            batch=f"{batch_num}/{total_batches}",
                            failed_items=len(batch_id_to_sku),
                        ).warning("Batch returned empty results")
                else:
                    all_results.append(batch_results)
                    logger.bind(
                        batch=f"{batch_num}/{total_batches}", results_count=1
                    ).success("Batch processed successfully (single result)")

            except Exception as exc:
                failed_skus.extend(batch_id_to_sku.values())
                logger.bind(
                    batch=f"{batch_num}/{total_batches}",
                    error=exc.__class__.__name__,
                    batch_start_idx=batch_idx,
                    failed_items=len(batch_id_to_sku),
                ).error("Failed to process batch, marking all items as failed")

        logger.bind(
            total_results=len(all_results), total_failed=len(failed_skus)
        ).info("Batch processing completed")

        return all_results, failed_skus
