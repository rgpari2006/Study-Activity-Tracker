"""Combined posture and object detection using YOLOv8 models."""

from typing import List, Set, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

from app.config import (
    CONFIDENCE_THRESHOLD,
    OBJECT_MODEL_NAME,
    PHONE_PROXIMITY_RATIO,
    POSE_MODEL_NAME,
)


class PoseDetector:
    """Detects human presence and classifies posture as sitting, standing, away, or undefined."""

    def __init__(
        self,
        model_name: str = POSE_MODEL_NAME,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ):
        self.model = YOLO(model_name)
        self.confidence_threshold = confidence_threshold
        self.last_wrists: List[Tuple[float, float]] = []

    def detect(self, frame: np.ndarray) -> Tuple[str, float, np.ndarray]:
        """Process a frame and return (posture_label, confidence, annotated_frame)."""
        self.last_wrists = []
        results = self.model(frame, imgsz=480, verbose=False)
        annotated_frame = frame.copy()

        if not results or len(results[0].boxes) == 0:
            cv2.putText(
                annotated_frame,
                "State: Away",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (180, 180, 180),
                2,
                cv2.LINE_AA,
            )
            return "away", 0.0, annotated_frame

        annotated_frame = results[0].plot()

        boxes = results[0].boxes
        confs = boxes.conf.cpu().numpy()
        best_idx = int(np.argmax(confs))
        best_conf = float(confs[best_idx])

        if best_conf < self.confidence_threshold:
            cv2.putText(
                annotated_frame,
                f"State: Undefined ({best_conf:.2f})",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (140, 140, 140),
                2,
                cv2.LINE_AA,
            )
            return "undefined", best_conf, annotated_frame

        box = boxes.xyxy.cpu().numpy()[best_idx]
        frame_h, frame_w = frame.shape[:2]
        box_h = (box[3] - box[1]) / frame_h
        box_top = box[1] / frame_h

        posture = "undefined"
        keypoints_data = results[0].keypoints

        if keypoints_data is not None and len(keypoints_data.data) > best_idx:
            kpts = keypoints_data.data[best_idx].cpu().numpy()

            # Extract wrists for phone proximity check
            wrists: List[Tuple[float, float]] = []
            for wrist_idx in (9, 10):
                if kpts[wrist_idx][2] > 0.35:
                    wrists.append((float(kpts[wrist_idx][0]), float(kpts[wrist_idx][1])))
            self.last_wrists = wrists

            l_shoulder_conf = kpts[5][2]
            r_shoulder_conf = kpts[6][2]
            l_hip_conf = kpts[11][2]
            r_hip_conf = kpts[12][2]
            l_knee_conf = kpts[13][2]
            r_knee_conf = kpts[14][2]

            shoulders_vis = l_shoulder_conf > 0.4 or r_shoulder_conf > 0.4
            hips_vis = l_hip_conf > 0.4 or r_hip_conf > 0.4
            knees_vis = l_knee_conf > 0.4 or r_knee_conf > 0.4

            shoulder_y = np.mean([kpts[i][1] for i in (5, 6) if kpts[i][2] > 0.4]) / frame_h if shoulders_vis else 0.5

            if knees_vis and hips_vis:
                hip_y = np.mean([kpts[i][1] for i in (11, 12) if kpts[i][2] > 0.4]) / frame_h
                knee_y = np.mean([kpts[i][1] for i in (13, 14) if kpts[i][2] > 0.4]) / frame_h
                thigh_v_dist = abs(knee_y - hip_y)
                if thigh_v_dist > 0.22 and box_h > 0.65:
                    posture = "standing"
                else:
                    posture = "sitting"
            elif hips_vis:
                hip_y = np.mean([kpts[i][1] for i in (11, 12) if kpts[i][2] > 0.4]) / frame_h
                torso_len = hip_y - shoulder_y
                if torso_len > 0.35 and shoulder_y < 0.25:
                    posture = "standing"
                else:
                    posture = "sitting"
            elif shoulders_vis:
                if shoulder_y < 0.20 and box_top < 0.05:
                    posture = "standing"
                else:
                    posture = "sitting"
            else:
                posture = "undefined"
        else:
            if box_h > 0.75 and box_top < 0.15:
                posture = "standing"
            elif box_h > 0.25:
                posture = "sitting"
            else:
                posture = "undefined"

        label_text = f"Activity: {posture.capitalize()} ({best_conf:.2f})"
        cv2.putText(
            annotated_frame,
            label_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (220, 220, 220),
            2,
            cv2.LINE_AA,
        )

        return posture, best_conf, annotated_frame


class StudyActivityDetector:
    """Detects human posture (sitting/standing/away/undefined) and study objects

    (laptop, book/paper, phone in hand, undefined).
    """

    CLASS_LAPTOP = 63
    CLASS_CELL_PHONE = 67
    CLASS_BOOK = 73

    def __init__(
        self,
        pose_model_name: str = POSE_MODEL_NAME,
        object_model_name: str = OBJECT_MODEL_NAME,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        phone_proximity_ratio: float = PHONE_PROXIMITY_RATIO,
    ):
        self.pose_detector = PoseDetector(pose_model_name, confidence_threshold)
        self.object_model = YOLO(object_model_name)
        self.confidence_threshold = confidence_threshold
        self.phone_proximity_ratio = phone_proximity_ratio

    def detect(self, frame: np.ndarray) -> Tuple[str, Set[str], np.ndarray]:
        """Process a frame and return (posture, detected_objects, annotated_frame)."""
        frame_h, frame_w = frame.shape[:2]

        posture, best_conf, annotated_frame = self.pose_detector.detect(frame)
        detected_objects: Set[str] = set()

        if posture != "away":
            # Re-use wrists directly from pose detection pass without re-running the model!
            wrists: List[Tuple[float, float]] = self.pose_detector.last_wrists

            obj_results = self.object_model(frame, imgsz=480, verbose=False)
            if obj_results and len(obj_results[0].boxes) > 0:
                boxes = obj_results[0].boxes
                classes = boxes.cls.cpu().numpy().astype(int)
                confs = boxes.conf.cpu().numpy()
                xyxy = boxes.xyxy.cpu().numpy()

                for cls_id, conf, bbox in zip(classes, confs, xyxy):
                    if conf < self.confidence_threshold:
                        if conf > 0.30 and cls_id in (self.CLASS_LAPTOP, self.CLASS_CELL_PHONE, self.CLASS_BOOK):
                            detected_objects.add("undefined")
                        continue

                    x1, y1, x2, y2 = bbox.astype(int)

                    if cls_id == self.CLASS_LAPTOP:
                        detected_objects.add("laptop")
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 180, 0), 2)
                        cv2.putText(
                            annotated_frame,
                            f"Laptop {conf:.2f}",
                            (x1, max(y1 - 8, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 180, 0),
                            2,
                            cv2.LINE_AA,
                        )

                    elif cls_id == self.CLASS_BOOK:
                        detected_objects.add("book/paper")
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
                        cv2.putText(
                            annotated_frame,
                            f"Book/Paper {conf:.2f}",
                            (x1, max(y1 - 8, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 200, 255),
                            2,
                            cv2.LINE_AA,
                        )

                    elif cls_id == self.CLASS_CELL_PHONE:
                        phone_cx = (x1 + x2) / 2.0
                        phone_cy = (y1 + y2) / 2.0

                        in_hand = False
                        if wrists:
                            diag = np.sqrt(frame_w**2 + frame_h**2)
                            for wx, wy in wrists:
                                dist = np.sqrt((phone_cx - wx)**2 + (phone_cy - wy)**2)
                                if dist < self.phone_proximity_ratio * diag:
                                    in_hand = True
                                    break
                        else:
                            in_hand = True

                        if in_hand:
                            detected_objects.add("phone in hand")
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                            cv2.putText(
                                annotated_frame,
                                f"Phone in hand {conf:.2f}",
                                (x1, max(y1 - 8, 20)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 165, 255),
                                2,
                                cv2.LINE_AA,
                            )
                        else:
                            detected_objects.add("undefined")

        summary_labels = [posture.capitalize()] + [obj.capitalize() for obj in sorted(detected_objects)]
        summary_text = " | ".join(summary_labels)
        cv2.putText(
            annotated_frame,
            summary_text,
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )

        return posture, detected_objects, annotated_frame
