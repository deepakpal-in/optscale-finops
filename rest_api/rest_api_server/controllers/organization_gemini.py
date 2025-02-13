import json
import logging
from typing import List

from clickhouse_driver import Client as ClickHouseClient
from rest_api.rest_api_server.controllers.base import BaseController, ClickHouseMixin
from rest_api.rest_api_server.controllers.base_async import BaseAsyncControllerWrapper
from rest_api.rest_api_server.models.models import OrganizationGemini


LOG = logging.getLogger(__name__)


class GeminiController(BaseController):
    """
    Controller for /restapi/v2/geminis/{id}
    """

    def _get_model_type(self):
        return OrganizationGemini


class GeminiAsyncController(BaseAsyncControllerWrapper):
    def _get_controller_class(self):
        return GeminiController


class GeminiDataController(BaseController, ClickHouseMixin):
    """
    Controller for /restapi/v2/geminis/{id}/data
    """
    @property
    def clickhouse_client(self):
        if not self._clickhouse_client:
            user, password, host, _ = self._config.clickhouse_params()
            self._clickhouse_client = ClickHouseClient(
                host=host, password=password, database="gemini", user=user)
        return self._clickhouse_client

    def get(self, gemini_id: str, buckets: list) -> list:
        unique_buckets = list(set(buckets))
        unique_buckets_length = len(unique_buckets)

        # The endpoint is intended to download duplicated records
        # for 1 (self duplicates) or 2 (cross duplicates) buckets
        result = []

        if unique_buckets_length == 1:
            result = self.execute_clickhouse(
                """SELECT tag, bucket, key, size
                    FROM gemini
                    WHERE id=%(gemini_id)s AND bucket=%(bucket)s
                    AND tag IN (SELECT tag FROM gemini GROUP BY tag HAVING COUNT(tag) > 1)
                """,
                params={"gemini_id": gemini_id, "bucket": unique_buckets[0]},
            )

            # Cannot use grouping in the query, we must return distinct rows at all times
            # "Post-grouping" - filter out records with 1 tag occurance (no self duplicates)
            tags = [row[0] for row in result]
            result = [row for row in result if tags.count(row[0]) > 1]

        if unique_buckets_length == 2:
            result = self.execute_clickhouse(
                """
                    SELECT tag, bucket, key, size
                    FROM gemini
                    WHERE id=%(gemini_id)s AND bucket IN %(buckets)s AND tag in (
                        SELECT tag
                        FROM gemini
                        WHERE id=%(gemini_id)s AND bucket=%(bucket_1)s

                        INTERSECT

                        SELECT tag
                        FROM gemini
                        WHERE id=%(gemini_id)s AND bucket=%(bucket_2)s
                    )
                """,
                params={
                    "gemini_id": gemini_id,
                    "buckets": unique_buckets,
                    "bucket_1": unique_buckets[0],
                    "bucket_2": unique_buckets[1],
                }
            )

        return [{"tag": r[0], "bucket": r[1],
                 "key": r[2], "size": r[3]} for r in result]


class GeminiDataAsyncController(BaseAsyncControllerWrapper):
    def _get_controller_class(self):
        return GeminiDataController


class GeminiDataAsyncController(BaseAsyncControllerWrapper):
    def _get_controller_class(self):
        return GeminiDataController


class OrganizationGeminiController(BaseController):
    """
    Controller for /restapi/v2/organizations/{id}/geminis and /restapi/v2/geminis
    """

    def _get_model_type(self) -> type:
        return OrganizationGemini

    def list(self, organization_id: str = None, **kwargs) -> List[OrganizationGemini]:
        if organization_id:
            return super().list(organization_id=organization_id)
        else:
            return super().list()

    def create(self, organization_id: str, filters: dict) -> OrganizationGemini:
        return super().create(organization_id=organization_id,
                              filters=json.dumps(filters))


class OrganizationGeminiAsyncController(BaseAsyncControllerWrapper):
    def _get_controller_class(self) -> type:
        return OrganizationGeminiController
