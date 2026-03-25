"""Тесты для methods/upload.py."""

from __future__ import annotations

from maxogram.enums import UploadType
from maxogram.methods.upload import GetUploadUrl
from maxogram.types.upload import UploadEndpoint


class TestGetUploadUrl:
    """Тесты POST /uploads — Получение URL для загрузки файла."""

    def test_metadata(self) -> None:
        assert GetUploadUrl.__api_path__ == "/uploads"
        assert GetUploadUrl.__http_method__ == "POST"
        assert GetUploadUrl.__returning__ is UploadEndpoint
        assert GetUploadUrl.__query_params__ == {"type_"}
        assert GetUploadUrl.__path_params__ == {}

    def test_create_with_type_(self) -> None:
        """Создание через Python-имя type_."""
        m = GetUploadUrl(type_=UploadType.IMAGE)
        assert m.type_ == "image"

    def test_create_with_alias(self) -> None:
        """Создание через alias 'type' (populate_by_name=True)."""
        m = GetUploadUrl(**{"type": "image"})
        assert m.type_ == "image"

    def test_create_all_upload_types(self) -> None:
        """Все значения UploadType работают."""
        for ut in UploadType:
            m = GetUploadUrl(type_=ut)
            assert m.type_ == ut.value

    def test_dump_by_alias(self) -> None:
        """model_dump(by_alias=True) содержит ключ 'type', не 'type_'."""
        m = GetUploadUrl(type_=UploadType.VIDEO)
        data = m.model_dump(by_alias=True)
        assert "type" in data
        assert "type_" not in data
        assert data["type"] == "video"

    def test_dump_by_name(self) -> None:
        """model_dump() без by_alias содержит ключ 'type_'."""
        m = GetUploadUrl(type_=UploadType.AUDIO)
        data = m.model_dump()
        assert "type_" in data
        assert data["type_"] == "audio"

    def test_body_empty(self) -> None:
        """Body пуст — type_ уходит в query params."""
        m = GetUploadUrl(type_=UploadType.FILE)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}
