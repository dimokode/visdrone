import cv2


def draw_detections(image_path, detections, class_colors=None):
    img = cv2.imread(image_path)

    for det in detections:
        xmin, ymin, xmax, ymax = det["bbox"]
        label = f'{det["class_name"]}: {det["confidence"]:.2f}'

        color = (0, 0, 255)
        if class_colors and det["class_id"] in class_colors:
            color = class_colors[det["class_id"]]

        cv2.rectangle(img, (xmin, ymin), (xmax, ymax), color, 2)
        cv2.putText(
            img,
            label,
            (xmin, max(ymin - 10, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )

    return img
