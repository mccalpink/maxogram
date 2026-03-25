"""Тесты State, StatesGroup, StatesGroupMeta."""

from __future__ import annotations

from maxogram.fsm.state import State, StatesGroup


class TestState:
    """State — описание одного состояния."""

    def test_str_representation(self) -> None:
        """State без группы — строка с '@' как группа."""

        class Form(StatesGroup):
            name = State()

        assert str(Form.name) == "Form:name"

    def test_none_state(self) -> None:
        """State с state=None — пустая строка через str()."""
        s = State()
        assert s.state is None
        assert str(s) == ""

    def test_wildcard_state(self) -> None:
        """State(state='*') — wildcard."""
        s = State(state="*")
        assert s.state == "*"
        assert str(s) == "*"

    def test_equality_same_state(self) -> None:
        """Два State с одинаковым именем равны."""

        class Form1(StatesGroup):
            name = State()

        class Form2(StatesGroup):
            name = State()

        # Разные группы — разные state
        assert Form1.name != Form2.name

    def test_equality_with_string(self) -> None:
        """State можно сравнивать со строкой."""

        class Form(StatesGroup):
            name = State()

        assert Form.name == "Form:name"
        assert Form.name != "Form:other"

    def test_hash(self) -> None:
        """State хэшируется по state строке."""

        class Form(StatesGroup):
            name = State()

        assert hash(Form.name) == hash("Form:name")

    def test_hash_wildcard(self) -> None:
        """Wildcard state хэшируется."""
        s = State(state="*")
        assert hash(s) == hash("*")

    def test_repr(self) -> None:
        """State repr."""

        class Form(StatesGroup):
            name = State()

        assert repr(Form.name) == "State('Form:name')"

    def test_group_property(self) -> None:
        """State.group возвращает группу-родителя."""

        class Form(StatesGroup):
            name = State()

        assert Form.name.group is Form

    def test_standalone_state_no_group(self) -> None:
        """State без группы — group=None."""
        s = State()
        assert s.group is None


class TestStatesGroup:
    """StatesGroup — группа состояний."""

    def test_states_tuple(self) -> None:
        """__states__ содержит только прямые состояния."""

        class Form(StatesGroup):
            a = State()
            b = State()

        assert len(Form.__states__) == 2
        assert Form.a in Form.__states__
        assert Form.b in Form.__states__

    def test_state_names(self) -> None:
        """__state_names__ содержит строковые имена."""

        class Form(StatesGroup):
            a = State()
            b = State()

        assert "Form:a" in Form.__state_names__
        assert "Form:b" in Form.__state_names__

    def test_contains_state(self) -> None:
        """Оператор 'in' проверяет принадлежность."""

        class Form(StatesGroup):
            a = State()

        assert Form.a in Form
        assert "Form:a" in Form

    def test_not_contains(self) -> None:
        """Оператор 'in' — отрицательный случай."""

        class Form(StatesGroup):
            a = State()

        assert "Form:b" not in Form

    def test_repr(self) -> None:
        """StatesGroup repr."""

        class Form(StatesGroup):
            a = State()

        assert repr(Form) == "<StatesGroup 'Form'>"


class TestNestedStatesGroup:
    """Вложенные StatesGroup."""

    def test_nested_full_name(self) -> None:
        """Вложенная группа имеет полное имя через точку."""

        class Dialog(StatesGroup):
            class Auth(StatesGroup):
                email = State()

        assert Dialog.Auth.email.state == "Dialog.Auth:email"

    def test_nested_all_states(self) -> None:
        """__all_states__ включает состояния вложенных групп."""

        class Dialog(StatesGroup):
            start = State()

            class Auth(StatesGroup):
                email = State()
                password = State()

        assert len(Dialog.__states__) == 1  # только start
        assert len(Dialog.__all_states__) == 3  # start + email + password

    def test_nested_all_states_names(self) -> None:
        """__all_states_names__ включает имена из вложенных."""

        class Dialog(StatesGroup):
            start = State()

            class Auth(StatesGroup):
                email = State()

        assert "Dialog:start" in Dialog.__all_states_names__
        assert "Dialog.Auth:email" in Dialog.__all_states_names__

    def test_nested_contains(self) -> None:
        """Вложенные состояния 'in' родительской группе."""

        class Dialog(StatesGroup):
            class Auth(StatesGroup):
                email = State()

        assert "Dialog.Auth:email" in Dialog

    def test_deeply_nested(self) -> None:
        """Трёхуровневая вложенность."""

        class Root(StatesGroup):
            class Level1(StatesGroup):
                class Level2(StatesGroup):
                    deep = State()

        assert Root.Level1.Level2.deep.state == "Root.Level1.Level2:deep"
        assert Root.Level1.Level2.deep in Root

    def test_nested_group_parent(self) -> None:
        """Вложенная группа: state.group указывает на непосредственного родителя."""

        class Dialog(StatesGroup):
            class Auth(StatesGroup):
                email = State()

        assert Dialog.Auth.email.group is Dialog.Auth


class TestWildcardState:
    """State(state='*') — wildcard."""

    def test_wildcard_not_in_group(self) -> None:
        """Wildcard state не принадлежит конкретной группе."""
        s = State(state="*")
        assert s.state == "*"
        assert s.group is None

    def test_wildcard_equality(self) -> None:
        """Два wildcard state равны."""
        s1 = State(state="*")
        s2 = State(state="*")
        assert s1 == s2
