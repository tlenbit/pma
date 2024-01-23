import logging
from dataclasses import dataclass

from config import Config
from models import Todo, Vault

# "б", "[" и "]" нету, потому что соответствующие им символы ломают парсинг alias-ов
# todo: пофиксить это?
translit_map = {
    "й": "q",
    "ц": "w",
    "у": "e",
    "к": "r",
    "е": "t",
    "н": "y",
    "г": "u",
    "ш": "i",
    "щ": "o",
    "з": "p",
    "ф": "a",
    "ы": "s",
    "в": "d",
    "а": "f",
    "п": "g",
    "р": "h",
    "о": "j",
    "л": "k",
    "д": "l",
    "ж": ";",
    "э": "'",
    "я": "z",
    "ч": "x",
    "с": "c",
    "м": "v",
    "и": "b",
    "т": "n",
    "ь": "m",
    "ю": ".",
}


def add_translited_name_to_notes_aliases(vault: Vault) -> None:
    for note in vault.get_notes():
        if not any(char.lower() in translit_map for char in note.name):
            continue

        aliases = list(note.get_aliases())
        translited_name = "".join(
            map(lambda s: translit_map.get(s.lower(), s.lower()), note.name)
        )
        aliases.append(translited_name)
        note.set_aliases(aliases)


def delete_duplicate_todos(vault: Vault) -> None:
    todos: dict[str, Todo] = {}

    for root_todo in vault.get_todos():
        for todo in root_todo.traverse():
            if todo.text in todos:
                logging.warning(f"Removing duplicate todo '{todo.text}'")
                present_todo = todos[todo.text]

                if todo.updated_at < present_todo.updated_at:
                    todo_that_remains = todo
                    todo_to_remove = present_todo
                else:
                    todo_that_remains = present_todo
                    todo_to_remove = todo

                todos[todo.text] = todo_that_remains
                todo_to_remove.delete()
            else:
                todos[todo.text] = todo


def ensure_meta_todos_present_in_every_project(vault: Vault) -> None:
    for project in vault.get_projects():
        project.add_default_todos()


def vault_has_no_duplicate_todos(vault: Vault) -> bool:
    return len(vault.get_all_todos()) == len(set(vault.get_all_todos()))


# todo: for every note
# check that either links from a note link to MOC
# or that MOC leads to the note
# def check_notes_dir_always_leads_to_MOC_dir(vault: Vault) -> None:
#     MOC_notes_names = {note.name for note in vault["MOC"].get_notes()}

#     for note in vault["notes"].get_notes():
#         internal_links = note.internal_links
#         parsed_internal_links = []
#         if not set(note.internal_links) & MOC_notes_names:
#             logging.error(
#                 f"Note {note} does not have link to MOC (it links only to {note.internal_links})"
#             )


def delete_all_done_todos(vault: Vault) -> None:
    def remove_subtodos(todo):
        for subtodo in todo.children:
            if subtodo.children:
                remove_subtodos(subtodo)
            if subtodo.done:
                todo.remove_child(subtodo)
                logging.info(f"Removing done todo: '{subtodo.text}'")

    for project_note in vault.get_projects():
        for todo in project_note.get_todos():
            remove_subtodos(todo)
            if todo.done:
                project_note.remove_todo(todo)
                logging.info(f"Removing done todo: '{todo.text}'")


@dataclass
class NotesConsistencyJob:
    vault: Vault
    config: Config

    def run(self):
        add_translited_name_to_notes_aliases(self.vault)
        ensure_meta_todos_present_in_every_project(self.vault)
        assert vault_has_no_duplicate_todos(self.vault)
        delete_all_done_todos(self.vault)
        # check_notes_dir_always_leads_to_MOC_dir(self.vault)
        # delete_duplicate_todos(self.vault)
