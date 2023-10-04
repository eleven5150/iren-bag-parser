import enum
import os
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

BAG_SIGNATURE: bytes = b"\x42\x41\x47\x1A"


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

    QUESTION_SIGNATURE: bytes = b"\x42\x41\x47\x1A\x0C\x00\x00\x00\x54\x65\x73\x74\x51\x75\x65\x73\x74\x69\x6F\x6E"

    @classmethod
    def database_to_test_questions(cls, database: Database) -> "TestQuestions":
        signature_len: int = len(cls.QUESTION_SIGNATURE)
        idx: int = database.data.find(cls.QUESTION_SIGNATURE)
        question_offsets: list[int] = list()
        while idx != -1:
            question_offsets.append(idx)
            idx = database.data.find(cls.QUESTION_SIGNATURE, idx + signature_len)

        questions: list["TestQuestion"] = list()
        for idx, offset in enumerate(question_offsets[:-1]):
            # with open(f"que_{idx}", "wb") as file:
            #     file.write(database.data[question_offsets[idx]:question_offsets[idx+1]])
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
        images_dir: Path = Path(dir_name / "images")
        os.mkdir(images_dir)
        with open(Path(dir_name / f"Answers_{dir_name}.md"), "wt") as out_file:
            picture_number: int = 1
            for question in self.questions:
                out_file.write(f"**{question.question}**\n\n")
                if question.answers[question.right_answer_idx].is_image:
                    with open(Path(images_dir / f"Picture_{picture_number}.png"), "wb") as picture_file:
                        picture_file.write(question.answers[question.right_answer_idx].answer)
                    out_file.write(f"![](images/Picture_{picture_number}.png)\n")
                    picture_number += 1
                else:
                    out_file.write(f">{question.answers[question.right_answer_idx].answer}\n")
                out_file.write("\n")
                out_file.write(f"-----------------------------------------------------------------------------------\n")
                out_file.write("\n")


@dataclass
class TestQuestion:
    question: list["Item"]
    answers: list["TestAnswer"]
    right_answer_idx: int

    ANSWER_SIGNATURE: bytes = b"\x42\x41\x47\x1A\x0A\x00\x00\x00\x54\x65\x73\x74\x41\x6E\x73\x77\x65\x72"

    NUM_OF_ITEMS_OFFSET: int = 0xBB
    FIRST_ITEM_OFFSET: int = 0xBF

    RIGHT_ANSWER_INDEX_OFFSET: int = 0x48

    @classmethod
    def data_to_test_question(cls, question_data: bytes) -> "TestQuestion":
        right_answer_idx: int = struct.unpack(
            ">I",
            question_data[cls.RIGHT_ANSWER_INDEX_OFFSET:cls.RIGHT_ANSWER_INDEX_OFFSET+4]
        )[0]

        num_of_items: int = struct.unpack(
            "<B",
            question_data[cls.NUM_OF_ITEMS_OFFSET:cls.NUM_OF_ITEMS_OFFSET + 1]
        )[0]
        curr_item_offset: int = cls.FIRST_ITEM_OFFSET
        question: list["Item"] = list()
        for idx in range(num_of_items):
            question.append(Item.data_to_item(question_data[curr_item_offset:]))
            curr_item_offset = question_data.find(BAG_SIGNATURE, curr_item_offset + len(BAG_SIGNATURE))

        answer_signature_length: int = len(cls.ANSWER_SIGNATURE)
        idx: int = question_data.find(cls.ANSWER_SIGNATURE)
        answers_offsets: list[idx] = list()
        while idx != -1:
            answers_offsets.append(idx)
            idx = question_data.find(cls.ANSWER_SIGNATURE, idx + answer_signature_length)

        answers: list["TestAnswer"] = list()
        for idx, offset in enumerate(answers_offsets[:-1]):
            answers.append(TestAnswer.data_to_test_answer(question_data[answers_offsets[idx]:answers_offsets[idx + 1]]))

        answers.append(TestAnswer.data_to_test_answer(question_data[answers_offsets[-1]:]))

        return cls(
            question=question,
            answers=answers,
            right_answer_idx=right_answer_idx
        )


@dataclass
class TestAnswer:
    answer: list["Item"]

    NUM_OF_ITEMS_OFFSET: int = 0x33
    FIRST_ITEM_OFFSET: int = 0x37

    @classmethod
    def data_to_test_answer(cls, answer_data: bytes) -> "TestAnswer":
        num_of_items: int = struct.unpack(
            "<B",
            answer_data[cls.NUM_OF_ITEMS_OFFSET:cls.NUM_OF_ITEMS_OFFSET + 1]
        )[0]
        curr_item_offset: int = cls.FIRST_ITEM_OFFSET
        answer: list["Item"] = list()
        for idx in range(num_of_items):
            answer.append(Item.data_to_item(answer_data[curr_item_offset:]))
            curr_item_offset = answer_data.find(BAG_SIGNATURE, curr_item_offset + len(BAG_SIGNATURE))

        return cls(
            answer=answer
        )


class ItemType(enum.Enum):
    TEXT: int = 0
    PICTURE: int = 1
    EMPTY: int = 2


class ItemTypeString(enum.Enum):
    TEXT: str = "TPO"
    PICTURE: str = "GPO"
    EMPTY: str = "LPO"


@dataclass
class Item:
    data: str | bytes
    type: int

    TYPE_OFFSET: int = 0x8
    TEXT_LENGTH_OFFSET: int = 0x17
    TEXT_DATA_OFFSET: int = 0x1B

    PICTURE_START_OFFSET: int = 0x1F
    PICTURE_END_SIGNATURE: bytes = b"\x49\x45\x4E\x44"

    @classmethod
    def data_to_item(cls, data: bytes) -> "Item":
        curr_item_type_str: str = str(
            data[cls.TYPE_OFFSET:cls.TYPE_OFFSET + 3],
            encoding="ascii"
        )

        if curr_item_type_str == ItemTypeString.TEXT.value:
            text_length: int = struct.unpack(
                "<I",
                data[cls.TEXT_LENGTH_OFFSET:cls.TEXT_LENGTH_OFFSET + 4]
            )[0]

            text_bytes: bytes = data[cls.TEXT_DATA_OFFSET:cls.TEXT_DATA_OFFSET + text_length]

            text: str = str(text_bytes, encoding="cp1251")
            if text[-1] == ' ':
                text = text[:-1]

            return cls(
                data=text,
                type=ItemType.TEXT
            )
        elif curr_item_type_str == ItemTypeString.PICTURE.value:
            iend_offset: int = data.find(cls.PICTURE_END_SIGNATURE)
            picture_len: int = iend_offset + 8 - cls.PICTURE_START_OFFSET

            picture_bytes: bytes = data[cls.PICTURE_START_OFFSET:cls.PICTURE_START_OFFSET+picture_len]

            return cls(
                data=picture_bytes,
                type=ItemType.PICTURE
            )
        elif curr_item_type_str == ItemTypeString.EMPTY.value:

            return cls(
                data="",
                type=ItemType.EMPTY
            )
        else:
            raise ValueError(f"Unknown item type {curr_item_type_str}")


def main(args: list[str]) -> None:
    in_file_path: Path = Path(args[1])
    database: Database = Database.exe_file_to_database(in_file_path)
    test_questions: TestQuestions = TestQuestions.database_to_test_questions(database)
    test_questions.export(database.name)


if __name__ == '__main__':
    main(sys.argv)
