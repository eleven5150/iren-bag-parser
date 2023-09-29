import os
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

        questions.append(
            TestQuestion.data_to_test_question(database.data[question_offsets[-1]:])
        )

        return cls(
            questions=questions
        )

    def export(self, name: str) -> None:
        dir_name: Path = Path(name[:-4])
        os.mkdir(dir_name)
        with open(Path(dir_name / f"Answers_{name}.txt"), "wt") as out_file:
            picture_number: int = 1
            for question in self.questions:
                out_file.write(f"Question -> {question.question}\n")
                if question.answers[question.right_answer_idx].is_image:
                    with open(Path(dir_name / f"Picture_{picture_number}.png"), "wb") as picture_file:
                        picture_file.write(question.answers[question.right_answer_idx].answer)
                    out_file.write(f"\t Answer -> Picture_{picture_number}\n")
                    picture_number += 1
                else:
                    out_file.write(f"\t Answer -> {question.answers[question.right_answer_idx].answer}\n")
                out_file.write("\n")
                out_file.write(f"-----------------------------------------------------------------------------------\n")
                out_file.write("\n")


@dataclass
class TestQuestion:
    question: str
    answers: list["TestAnswer"]
    right_answer_idx: int

    SIGNATURE: bytes = b"\x42\x41\x47\x1A\x0C\x00\x00\x00\x54\x65\x73\x74\x51\x75\x65\x73\x74\x69\x6F\x6E"
    QUESTION_LENGTH_OFFSET: int = 0xD6
    QUESTION_STRING_OFFSET: int = 0xDA

    RIGHT_ANSWER_INDEX_OFFSET: int = 0x47

    @classmethod
    def data_to_test_question(cls, question_data: bytes) -> "TestQuestion":
        question_length: int = struct.unpack(
            "<I",
            question_data[cls.QUESTION_LENGTH_OFFSET:cls.QUESTION_LENGTH_OFFSET+4]
        )[0]

        question_bytes: bytes = question_data[cls.QUESTION_STRING_OFFSET:cls.QUESTION_STRING_OFFSET+question_length]
        question: str = str(question_bytes, encoding="cp1251")

        signature_length: int = len(TestAnswer.SIGNATURE)
        idx: int = question_data.find(TestAnswer.SIGNATURE)
        answers_offsets: list[idx] = list()
        while idx != -1:
            answers_offsets.append(idx)
            idx = question_data.find(TestAnswer.SIGNATURE, idx + signature_length)

        answers: list["TestAnswer"] = list()
        for idx, offset in enumerate(answers_offsets[:-1]):
            answers.append(TestAnswer.data_to_test_answer(question_data[answers_offsets[idx]:answers_offsets[idx + 1]]))

        answers.append(TestAnswer.data_to_test_answer(question_data[answers_offsets[-1]:]))

        right_answer_idx: int = struct.unpack(
            "<I",
            question_data[cls.RIGHT_ANSWER_INDEX_OFFSET:cls.RIGHT_ANSWER_INDEX_OFFSET+4]
        )[0]

        return cls(
            question=question,
            answers=answers,
            right_answer_idx=right_answer_idx
        )


@dataclass
class TestAnswer:
    answer: str | bytes
    is_image: bool

    SIGNATURE: bytes = b"\x42\x41\x47\x1A\x0A\x00\x00\x00\x54\x65\x73\x74\x41\x6E\x73\x77\x65\x72"

    ANSWER_TYPE_OFFSET: int = 0x3F
    ANSWER_LENGTH_OFFSET: int = 0x4E

    TEXT_ANSWER_SIGNATURE: str = "TPO"
    TEXT_ANSWER_STRING_OFFSET: int = 0x52

    PICTURE_ANSWER_SIGNATURE: str = "GPO"
    PICTURE_ANSWER_GAP: int = 0xD

    @classmethod
    def data_to_test_answer(cls, answer_data: bytes) -> "TestAnswer":

        answer_type: str = str(answer_data[cls.ANSWER_TYPE_OFFSET:cls.ANSWER_TYPE_OFFSET+3], encoding="ascii")

        answer_length: int = struct.unpack(
            "<H",
            answer_data[cls.ANSWER_LENGTH_OFFSET:cls.ANSWER_LENGTH_OFFSET + 2]
        )[0]
        answer_bytes: bytes = answer_data[cls.TEXT_ANSWER_STRING_OFFSET:cls.TEXT_ANSWER_STRING_OFFSET + answer_length]

        if answer_type == cls.TEXT_ANSWER_SIGNATURE:
            is_image: bool = False
            answer: str = str(answer_bytes, encoding="cp1251")
        elif answer_type == cls.PICTURE_ANSWER_SIGNATURE:
            is_image: bool = True
            answer: bytes = answer_bytes[cls.PICTURE_ANSWER_GAP:]
        else:
            raise ValueError(f"Unknown answer type {answer_type}")

        return cls(
            answer=answer,
            is_image=is_image
        )


def main(args: list[str]) -> None:
    in_file_path: Path = Path(args[1])
    database: Database = Database.exe_file_to_database(in_file_path)
    test_questions: TestQuestions = TestQuestions.database_to_test_questions(database)
    test_questions.export(database.name)


if __name__ == '__main__':
    main(sys.argv)
