from rest_framework import serializers

from .models import Dataset, Indicator, Layer


class DatasetSerializer(serializers.ModelSerializer):
    last_data_date = serializers.SerializerMethodField()
    last_ingested_at = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "key",
            "name",
            "provider",
            "licence",
            "url",
            "update_cadence",
            "access_level",
            "status",
            "last_data_date",
            "last_ingested_at",
        ]

    def get_last_data_date(self, obj: Dataset):
        v = obj.latest_version
        return v.data_date if v else None

    def get_last_ingested_at(self, obj: Dataset):
        v = obj.latest_version
        return v.ingested_at if v else None


class IndicatorSerializer(serializers.ModelSerializer):
    dataset = serializers.SlugRelatedField(slug_field="key", read_only=True)

    class Meta:
        model = Indicator
        fields = [
            "key",
            "name",
            "unit",
            "theme",
            "value_chain",
            "temporal",
            "agg_method",
            "higher_is_better",
            "classes",
            "method_doc",
            "is_provisional",
            "dataset",
        ]


class LayerSerializer(serializers.ModelSerializer):
    indicator = serializers.SlugRelatedField(slug_field="key", read_only=True)
    source = serializers.SerializerMethodField()

    class Meta:
        model = Layer
        fields = [
            "key",
            "name",
            "kind",
            "theme",
            "indicator",
            "vector_source",
            "style",
            "legend",
            "roles",
            "default_on",
            "sort_order",
            "source",
        ]

    def get_source(self, obj: Layer) -> dict | None:
        ds = obj.dataset or (obj.indicator.dataset if obj.indicator else None)
        if ds is None:
            return None
        v = ds.latest_version
        return {
            "dataset": ds.key,
            "name": ds.name,
            "provider": ds.provider,
            "licence": ds.licence,
            "status": ds.status,
            "data_date": v.data_date if v else None,
        }
