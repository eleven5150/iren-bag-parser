import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Database:
    name: str
    data: bytes

    DATABASE_OFFSET: int = 0x70C10

    @classmethod
    def exe_file_to_database(cls, in_file_path: Path) -> "Database":
        with open(in_file_path, "rb") as in_file:
            exe_data: bytes = in_file.read()
        compr_data: bytes = exe_data[cls.DATABASE_OFFSET:]
        decompr_data: bytes = zlib.decompress(compr_data)
        return cls(
            name=in_file_path.name,
            data=decompr_data
        )


def main(args: list[str]) -> None:
    in_file_path: Path = Path(args[1])
    database: Database = Database.exe_file_to_database(in_file_path)




if __name__ == '__main__':
    main(sys.argv)