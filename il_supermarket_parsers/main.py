from .multiprocess_pharser import ParallelParser
from .utils.logger import Logger


class ConvertingTask:
    """main convert task"""

    def __init__(
        self, data_folder="dumps", multiprocessing=6
    ):
        Logger.info(
            f"Starting Parser, data_folder={data_folder},"
            f"number_of_processes={multiprocessing}"
        )
        self.runner = ParallelParser(
            data_folder,
            multiprocessing=multiprocessing,
        )

    def start(self):
        """run the parsing"""
        return self.runner.execute()
    

if __name__ == "__main__":
    ConvertingTask()
