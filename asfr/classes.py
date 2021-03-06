import os
import eel
import cv2
import pickle
import base64
import numpy as np
from typing import Type
from pathlib import Path
from datetime import datetime
import face_recognition as fr
from khayyam import JalaliDate
from concurrent.futures import ProcessPoolExecutor


class ASFR(object):
    """ Attendance system using facial recognition """
    def __init__(self):
        self.images_list = []
        self.known_faces_encodes = []
        self.cl_names = []
        self.cap = cv2.VideoCapture(0)
        self.stream = True

    def image_loader(self, path="../train_images") -> None:
        """
        Loading images from given directory.
        :param path: str, address of images directory
                    default value: train_images directory
        :return: None
        """
        # Adding list of contents to a list
        list_of_contents = os.listdir(path)
        for cl in list_of_contents:
            current_image = cv2.imread(f"{path}/{cl}")
            self.images_list.append(current_image)
            # dropping the file extension
            self.cl_names.append(os.path.splitext(cl)[0])

    @staticmethod
    def _encoder(image: Type[np.ndarray]) -> Type[np.ndarray]:
        """
        Find encodings for each image (this is a protected function).
        :param image: numpy ndarray, loaded image
        :return: numpy ndarray, encode value
        """
        # convert BGR to RGB
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        encode = fr.face_encodings(img)[0]
        return encode

    def encoder(self) -> None:
        """
        Executes protected function for all images in train directory
        :return: None
        """
        percent = 0     # default percentage value
        with ProcessPoolExecutor() as executor:
            for enc in executor.map(self._encoder, self.images_list):
                self.known_faces_encodes.append(enc)
                percent = (len(self.known_faces_encodes) / len(self.images_list)) * 100
                eel.updateProgress(percent)

    def save(self) -> None:
        """
        Saves encodings and names into files.
        :return: None
        """
        # opening data_file and names and pickling to them
        with open("../data/data_file", "wb") as dump:
            dump.write(pickle.dumps(self.known_faces_encodes))
            dump.flush()
        with open("../data/names", "wb") as file:
            file.write(pickle.dumps(self.cl_names))
            file.flush()

    @staticmethod
    def csv_creator() -> None:
        """
        Creates a csv file for today attendances.
        :return: None
        """
        Path("../statistics").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(f"../statistics/{str(JalaliDate.today())}.csv"):
            with open(f"../statistics/{str(JalaliDate.today())}.csv", "w") as file:
                file.writelines("Name,Time")
                file.flush()

    @staticmethod
    def attendance_marker(name_of_person: str) -> None:
        """
        Opens the csv file and insert the name and arrive time to file.
        :param name_of_person: str, name of the person whom recognized
                                by the algorithm
        :return: None
        """
        fmt = "%H:%M:%S"  # time format
        with open(f"../statistics/{str(JalaliDate.today())}.csv", "r+") as file:
            my_data_list = file.readlines()
            # declaring two empty lists to store previous records
            names = []
            times = []
            for line in my_data_list[1:]:  # skipping first row(Name,Time)
                line = line.strip()  # skipping new line character
                entry = line.split(",")
                names.append(entry[0])
                times.append(entry[1])
            if name_of_person not in names:
                now = datetime.now()
                date_string = now.strftime(fmt)
                file.writelines(f"\n{name_of_person},{date_string}")
                file.flush()
            else:
                # When name of person previously stored in csv file
                now = datetime.now()
                now_str = datetime.strftime(now, fmt)
                now_time = datetime.strptime(now_str, fmt)
                for name, time in zip(list(reversed(names)), list(reversed(times))):
                    if name == name_of_person:
                        latest_time_str = time.strip()
                        latest_time = datetime.strptime(latest_time_str, fmt)
                        delta = (now_time - latest_time).total_seconds()
                        break  # breaks for loop when first wanted record is found
                if delta > 30.0:  # if 30 seconds have elapsed since the last arrival
                    file.writelines(f"\n{name_of_person},{now_str}")
                    file.flush()

    def recognizer(self) -> None:
        """
        Opens default camera and starts recognition process
        :return: None
        """

        with open("../data/data_file", "rb") as file_1:
            my_data = pickle.loads(file_1.read())
        with open("../data/names", "rb") as file_2:
            unpickled_names = pickle.loads(file_2.read())

        # creating a csv file
        self.csv_creator()
        self.stream = True

        while self.stream is True:
            _, img = self.cap.read()  # _: True if the frame is read correctly, otherwise False
            # making small - quarter
            small_image = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            # converting BGR to RGB
            small_image = cv2.cvtColor(small_image, cv2.COLOR_BGR2RGB)
            # finding face locations in the current frame
            faces_in_current_frame = fr.face_locations(small_image)
            # encoding faces that are located in the current frame
            encodings_in_current_frame = fr.face_encodings(
                small_image, faces_in_current_frame)

            for encode_face, face_location in zip(encodings_in_current_frame, faces_in_current_frame):
                # comparing faces
                matches = fr.compare_faces(my_data, encode_face)
                # calculating the distance
                face_distance = fr.face_distance(my_data, encode_face)
                # finding the index of minimum value (correct encoding)
                index_of_match = np.argmin(face_distance)

                if matches[index_of_match]:
                    # capitalizing the name of person
                    name = unpickled_names[int(index_of_match)].upper()
                    y_1, x_2, y_2, x_1 = face_location
                    # undoing making small image - Quadruple
                    y_1, x_2, y_2, x_1 = y_1 * 4, x_2 * 4, y_2 * 4, x_1 * 4
                    # image itself, start_point, end_point, color, thickness
                    cv2.rectangle(img, (x_1, y_1), (x_2, y_2), (0, 255, 0), 2)
                    # image itself, text string, coordinate of text, font type, font scale, color, thickness
                    cv2.putText(img, name, (x_1 + 6, y_2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1,
                                (255, 255, 255), 2)
                    # inserting the name and the time to csv file
                    self.attendance_marker(name)
                else:
                    # unpacking face location
                    y_1, x_2, y_2, x_1 = face_location
                    # undoing making small image - Quadruple
                    y_1, x_2, y_2, x_1 = y_1 * 4, x_2 * 4, y_2 * 4, x_1 * 4
                    cv2.rectangle(img, (x_1, y_1), (x_2, y_2), (0, 0, 255), 2)
                    cv2.putText(img, "Unknown Face!", (x_1 + 6, y_2 - 6),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)

            _, jpeg = cv2.imencode(".jpg", img)
            blob = base64.b64encode(jpeg.tobytes())
            blob = blob.decode("utf-8")
            eel.updateImageSrc(blob)()

    def stop(self) -> None:
        """
        Stops capturing video
        :return: None
        """
        self.cap.release()
        self.stream = False
        self.cap = cv2.VideoCapture(0)
