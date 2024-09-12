import os
from queue import Empty
from .utils import DataLoader
from .parser_factroy import ParserFactory


class StoreParseingPipeline:
    """
    processing a store data
    """

    def __init__(self, folder, store_enum, file_type) -> None:
        self.store_enum = store_enum
        self.file_type = file_type
        self.folder = folder
        self.database = FileStore(self.store_enum.name)

    def process(self):
        parser = self.store_enum.value()
        for file in DataLoader(self.folder, store_names=[self.store_enum.name],files_types=[self.file_type]).load():
            file.data = parser.read(file)
            yield file




    def convert(self, full_path, file_type, update_date):
        """convert xml to database"""
        #
        try:
            id_field_name = xml.get_key_column()

            if not self.database.is_file_already_processed(full_path):

                # check there is not file that process after it.
                self.database.validate_all_data_source_processed_was_before(update_date)

                # insert line by line
                try:
                    if os.path.getsize(full_path) == 0:
                        raise Empty(f"File {full_path} is empty.")

                    raw = xml.convert(full_path)

                    if xml.should_convert_to_incremental():

                        # get the last not deleted entriees
                        not_deleted_entries = self.database.get_store_last_state(
                            id_field_name
                        )
                        #
                        if id_field_name not in raw.columns:
                            raise ValueError("pharse error, no id field")

                        for _, line in raw.iterrows():

                            # remove the Id from the list of doc in the collection
                            doc_id = line[id_field_name]

                            if doc_id in not_deleted_entries:
                                not_deleted_entries.remove(doc_id)

                            existing_doc = self.database.find_one_doc(
                                id_field_name, line[id_field_name]
                            )
                            insert_doc = line[line != "NOT_APPLY"].to_dict()

                            if not existing_doc or self.database.document_had_changed(
                                insert_doc, existing_doc
                            ):

                                # if there exits a document -> found a change
                                if existing_doc:
                                    print(
                                        f"Found an update for {existing_doc[id_field_name]}: \n"
                                        f"{self.database.diff_document(insert_doc,existing_doc)}\n"
                                    )

                                # insert with new update
                                self.database.insert_one_doc(insert_doc, update_date)

                        # mark deleted for the document left.
                        for entry_left in not_deleted_entries:
                            self.database.update_one_doc(
                                {id_field_name: entry_left},
                                id_field_name,
                                mark_deleted=True,
                            )
                    else:
                        # simpley add all
                        for _, line in raw.iterrows():
                            self.database.insert_one_doc(line.to_dict(), update_date)
                except Empty as error:
                    self.database.insert_file_processed(
                        {
                            "execption": str(error),
                            **self._to_doc(
                                full_path, file_type, update_date, id_field_name
                            ),
                        }
                    )
                else:
                    # update when all is done
                    self.database.insert_file_processed(
                        self._to_doc(full_path, file_type, update_date, id_field_name)
                    )
            return True
        except Exception as error:
            self.database.insert_failure(
                {
                    "execption": str(error),
                    **self._to_doc(full_path, file_type, update_date, id_field_name),
                }
            )
            return False

    def _to_doc(self, full_path, file_type, update_date, id_field_name):
        return {
            "full_path": full_path,
            "update_date": update_date,
            "branch_store_id": self.branch_store_id,
            "store_name": self.store_name,
            "file_type": file_type,
            "id_field_name": id_field_name,
        }
