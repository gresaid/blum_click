import math
import random
import time

import cv2
import keyboard
import mss
import numpy as np
import pyautogui
import win32api
import win32con
import win32gui


class Logger:
    def __init__(self, prefix=None):
        self.prefix = prefix

    def log(self, data: str):
        if self.prefix:
            print(f"{self.prefix} {data}")
        else:
            print(data)

    def input(self, text: str):
        if self.prefix:
            return input(f"{self.prefix} {text}")
        else:
            return input(text)


class AutoClicker:
    def __init__(self, target_colors_hex, nearby_colors_hex, logger, percentages: float,
                 ):
        self.target_colors_hex = target_colors_hex
        self.nearby_colors_hex = nearby_colors_hex
        self.logger = logger
        self.running = False
        self.clicked_points = []
        self.iteration_count = 0
        self.percentage_click = percentages

        self.target_hsvs = [self.hex_to_hsv(color) for color in self.target_colors_hex]
        self.nearby_hsvs = [self.hex_to_hsv(color) for color in self.nearby_colors_hex]

    @staticmethod
    def hex_to_hsv(hex_color):
        hex_color = hex_color.lstrip('#')
        h_len = len(hex_color)
        rgb = tuple(int(hex_color[i:i + h_len // 3], 16) for i in range(0, h_len, h_len // 3))
        rgb_normalized = np.array([[rgb]], dtype=np.uint8)
        hsv = cv2.cvtColor(rgb_normalized, cv2.COLOR_RGB2HSV)
        return hsv[0][0]

    @staticmethod
    def click_at(x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def toggle_script(self):
        self.running = not self.running
        r_text = "Enabled" if self.running else "Disabled"
        self.logger.log(f'Status changed: {r_text}')

    @staticmethod
    def is_near_color(hsv_img, center, target_hsvs, radius=8):
        x, y = center
        height, width = hsv_img.shape[:2]
        for i in range(max(0, x - radius), min(width, x + radius + 1)):
            for j in range(max(0, y - radius), min(height, y + radius + 1)):
                distance = math.sqrt((x - i) ** 2 + (y - j) ** 2)
                if distance <= radius:
                    pixel_hsv = hsv_img[j, i]
                    for target_hsv in target_hsvs:
                        if np.allclose(pixel_hsv, target_hsv, atol=[1, 50, 50]):
                            return True
        return False

    def click_color_areas(self):
        screen_width, screen_height = pyautogui.size()
        center_x, center_y = screen_width // 2, screen_height // 2
        region_width, region_height = 380, 650
        region_left = center_x - region_width // 2
        region_top = center_y - region_height // 2
        cv2.namedWindow("Put blumapp here", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Put blumapp here", region_width, region_height)
        print("Put blum app in the window. Don't move the window. Then press any key to start")
        hwnd = win32gui.FindWindow(None, "Put blumapp here")
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, int(255 * 0.5), win32con.LWA_ALPHA)
        cv2.imshow("Put blumapp here", np.zeros((region_height, region_width, 3), dtype=np.uint8))
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        with mss.mss() as sct:
            grave_key_code = 41
            keyboard.add_hotkey(grave_key_code, self.toggle_script)
            while True:
                if self.running:
                    monitor = {
                        "top": region_top,
                        "left": region_left,
                        "width": region_width,
                        "height": region_height
                    }
                    img = np.array(sct.grab(monitor))
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
                    for target_hsv in self.target_hsvs:
                        lower_bound = np.array([max(0, target_hsv[0] - 1), 30, 30])
                        upper_bound = np.array([min(179, target_hsv[0] + 1), 255, 255])
                        mask = cv2.inRange(hsv, lower_bound, upper_bound)
                        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                        for contour in reversed(contours):
                            if random.random() >= self.percentage_click:
                                continue
                            if cv2.contourArea(contour) < 8:
                                continue
                            M = cv2.moments(contour)
                            if M["m00"] == 0:
                                continue
                            cX = int(M["m10"] / M["m00"]) + monitor["left"]
                            cY = int(M["m01"] / M["m00"]) + monitor["top"]
                            if not self.is_near_color(hsv, (cX - monitor["left"], cY - monitor["top"]),
                                                      self.nearby_hsvs):
                                continue
                            if any(math.sqrt((cX - px) ** 2 + (cY - py) ** 2) < 35 for px, py in self.clicked_points):
                                continue
                            cY += 7
                            self.click_at(cX, cY)
                            self.logger.log(f'Click at: {cX} {cY}')
                            self.clicked_points.append((cX, cY))

                    time.sleep(0.222)
                    self.iteration_count += 1


if __name__ == "__main__":
    logger = Logger("[t.me/cryptofolkens]")
    PERCENTAGES = {
        "1": 0.13,
        "2": 0.17,
        "3": 0.235,
        "4": 1,
    }
    answer = None
    while answer is None:
        points_key = logger.input(
            "Blum points"
            "1: 90-110  2: 140-160 3: 170-180 4: MAX: ")
        answer = PERCENTAGES.get(points_key, None)
        if answer is None:
            logger.log("Error values")
    percentages = answer
    logger.log('Press ` ')
    target_colors_hex = ["#c9e100", "#bae70e"]
    nearby_colors_hex = ["#abff61", "#87ff27"]
    auto_clicker = AutoClicker(target_colors_hex, nearby_colors_hex, logger, percentages=percentages,
                               )
    try:
        auto_clicker.click_color_areas()
    except Exception as e:
        logger.log(f"Panic error: {e}")
    for i in reversed(range(5)):
        i += 1
        print(f"Exit {i}")
        time.sleep(1)
