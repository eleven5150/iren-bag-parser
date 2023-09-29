import struct
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


@dataclass
class TestQuestions:
    questions: list["TestQuestion"]



    @classmethod
    def database_to_test_questions(cls, database: Database) -> "TestQuestions":
        signature_len: int = len(TestQuestion.SIGNATURE)
        idx: int = database.data.find(TestQuestion.SIGNATURE)
        question_offsets: list[int] = list()
        while idx != -1:
            question_offsets.append(idx)
            idx = database.data.find(TestQuestion.SIGNATURE, idx + signature_len)

        questions: list["TestQuestion"] = list()
        for idx, offset in enumerate(question_offsets[:-1]):
            questions.append(
                TestQuestion.data_to_test_question(database.data[question_offsets[idx]:question_offsets[idx+1]])
            )




@dataclass
class TestQuestion:
    question: str
    answers: list["TestAnswer"]
    true_answer_idx: int

    SIGNATURE: bytes = b"\x42\x41\x47\x1A\x0C\x00\x00\x00\x54\x65\x73\x74\x51\x75\x65\x73\x74\x69\x6F\x6E"
    QUESTION_LENGTH_OFFSET: int = 0xD6
    QUESTION_STRING_OFFSET: int = 0xDA

    @classmethod
    def data_to_test_question(cls, question_data: bytes) -> "TestQuestion":
        question_length: int = struct.unpack(
            "<I",
            question_data[cls.QUESTION_LENGTH_OFFSET:cls.QUESTION_LENGTH_OFFSET+4]
        )[0]

        question_bytes: bytes = question_data[cls.QUESTION_STRING_OFFSET:cls.QUESTION_STRING_OFFSET+question_length]
        question: str = str(question_bytes, encoding="cp1251")
        print("kek")



@dataclass
class TestAnswer:
    answer_data: bytes


def main(args: list[str]) -> None:
    in_file_path: Path = Path(args[1])
    database: Database = Database.exe_file_to_database(in_file_path)
    test_questions: TestQuestions = TestQuestions.database_to_test_questions(database)



if __name__ == '__main__':
    main(sys.argv)