# import statements
import pickle
from typing import List


def save_encodings(encodings: List, class_names: List):
    """
    save encodings into a file
    :param class_names: class names of images
    :param encodings: list of generated encodings
    :return: None
    """
    # opening data_file and names and pickling to them
    with open("./data/data_file", "wb") as dump:
        dump.write(pickle.dumps(encodings))
    with open("./data/names", "wb") as f:
        f.write(pickle.dumps(class_names))