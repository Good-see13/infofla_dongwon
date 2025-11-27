from typing import Optional, Tuple

import cv2
from src.core.config import WINDOW_NAME, MAX_DISPLAY_DETECTIONS, WINDOW_SCALE

class DisplayManager:
    
    def __init__(
        self,
        window_name: Optional[str] = None,
        max_display: Optional[int] = None,
        window_scale: Optional[float] = None,
        create_window: bool = True,
    ):
        self.window_name = window_name or WINDOW_NAME
        self.max_display = max_display or MAX_DISPLAY_DETECTIONS
        scale = WINDOW_SCALE if window_scale is None else window_scale
        self.window_scale = scale if scale and scale > 0 else 1.0
        self._window_created = False
        if create_window:
            self._create_window()
    
    def _create_window(self):
        if not self._window_created:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            self._window_created = True
    
    def _put_text(self, img, text, pos, color=(255, 255, 255), size=0.5, thickness=2):
        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, size, color, thickness)

    def _put_wrapped_text(
        self,
        img,
        text,
        pos,
        max_width,
        color=(255, 255, 255),
        size=0.6,
        thickness=2,
        line_gap=28,
    ):
        """Draw multiline text that wraps at max_width"""
        if not text:
            return pos[1]
        words = text.split()
        line = ""
        y = pos[1]
        for word in words:
            candidate = (line + " " + word).strip()
            width, _ = cv2.getTextSize(candidate, cv2.FONT_HERSHEY_SIMPLEX, size, thickness)[0]
            if width <= max_width:
                line = candidate
            else:
                if line:
                    self._put_text(img, line, (pos[0], y), color, size, thickness)
                    y += line_gap
                line = word
        if line:
            self._put_text(img, line, (pos[0], y), color, size, thickness)
            y += line_gap
        return y
    
    def _draw_button(
        self,
        img,
        top_left: Tuple[int, int],
        bottom_right: Tuple[int, int],
        label: str,
        color=(60, 180, 75),
        hover=False,
    ):
        fill_color = tuple(min(255, c + 40) for c in color) if hover else color
        cv2.rectangle(img, top_left, bottom_right, fill_color, -1)
        cv2.rectangle(img, top_left, bottom_right, (255, 255, 255), 2)
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        text_x = top_left[0] + (bottom_right[0] - top_left[0] - text_size[0]) // 2
        text_y = top_left[1] + (bottom_right[1] - top_left[1] + text_size[1]) // 2
        self._put_text(img, label, (text_x, text_y), (0, 0, 0), 0.8, 2)
    
    def draw_info(self, plots, model_name, model_color, detections, frame_count, capture_count):
        self._put_text(plots, f"Model: {model_name}", (10, 30), model_color)
        self._put_text(plots, f"Frame: {frame_count}", (10, 60))
    
    def draw_detections(self, plots, results, max_display=None):
        max_display = max_display or self.max_display
        if results[0].boxes is not None:
            for i, box in enumerate(results[0].boxes[:max_display]):
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = results[0].names[class_id]
                self._put_text(plots, f"{class_name}: {confidence:.2f}", (10, 180 + i*20), (0, 255, 0), 0.3, 1)
    
    def draw_bbox_on_image(self, img, detections, model_name):
        """Draw bounding boxes on image with labels"""
        result = img.copy()
        
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            
            cv2.rectangle(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            self._put_text(result, label, (x1, y1 - 5), (0, 0, 0), 0.5)
        
        self._put_text(result, f"Model: {model_name}", (10, 30), (0, 255, 0), 0.7)
        self._put_text(result, f"Detections: {len(detections)}", (10, 60), (0, 255, 0), 0.7)
        
        return result
    
    def show_analyzing_message(self, plots, message="ANALYZING...", show_subtitle=True):
        """Display analyzing message overlay with background"""
        frame = plots.copy()
        h, w = frame.shape[:2]
        
        # Semi-transparent dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # Large centered text
        text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = (w - text_size[0]) // 2
        text_y = (h + text_size[1]) // 2
        
        # Text shadow
        self._put_text(frame, message, (text_x + 3, text_y + 3), (0, 0, 0), 1.5, 3)
        # Main text
        self._put_text(frame, message, (text_x, text_y), (0, 255, 255), 1.5, 3)
        
        if show_subtitle:
            subtitle = "Please wait (2-5s)..."
            sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            sub_x = (w - sub_size[0]) // 2
            sub_y = text_y + 50
            self._put_text(frame, subtitle, (sub_x, sub_y), (255, 255, 255), 0.7, 2)
        
        return frame
    
    def show_confirmation_prompt(self, plots, summary_lines, prompt):
        """Render confirmation dialog with YES/NO buttons and return True/False"""
        frame = plots.copy()
        h, w = frame.shape[:2]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        
        title_y = max(80, h // 6)
        self._put_text(frame, "ANALYSIS SUMMARY", (60, title_y), (0, 255, 255), 1.0, 3)
        y = title_y + 50
        summary_box_width = int(w * 0.8)
        for line in summary_lines:
            text = line.strip()
            if text:
                y = self._put_wrapped_text(frame, text, (60, y), summary_box_width, (255, 255, 255), 0.75, 2, 34)
            else:
                y += 28
        
        prompt_y = y + 20
        self._put_text(frame, prompt, (60, prompt_y), (0, 200, 255), 0.7, 2)
        
        button_width = 200
        button_height = 80
        horizontal_margin = int(w * 0.15)
        button_y1 = max(prompt_y + 80, h - 160)
        if button_y1 + button_height + 40 > h:
            button_y1 = max(h - button_height - 60, prompt_y + 40)
        yes_rect = ((horizontal_margin, button_y1),
                    (horizontal_margin + button_width, button_y1 + button_height))
        no_rect = ((w - horizontal_margin - button_width, button_y1),
                   (w - horizontal_margin, button_y1 + button_height))
        
        self._draw_button(frame, yes_rect[0], yes_rect[1], "YES")
        self._draw_button(frame, no_rect[0], no_rect[1], "NO", color=(50, 90, 200))
        self._put_text(frame, "키보드: Y / N", (w // 2 - 70, button_y1 + button_height + 40), (255, 255, 255), 0.6, 2)
        
        choice = {"value": None}
        
        self._create_window()
        
        def on_mouse(event, x, y, *_):
            if event == cv2.EVENT_LBUTTONDOWN:
                if yes_rect[0][0] <= x <= yes_rect[1][0] and yes_rect[0][1] <= y <= yes_rect[1][1]:
                    choice["value"] = True
                elif no_rect[0][0] <= x <= no_rect[1][0] and no_rect[0][1] <= y <= no_rect[1][1]:
                    choice["value"] = False
        
        cv2.setMouseCallback(self.window_name, on_mouse)
        try:
            while choice["value"] is None:
                self.show(frame)
                key = self.wait_key(50) & 0xFF
                if key in (ord('y'), ord('Y')):
                    choice["value"] = True
                elif key in (ord('n'), ord('N')):
                    choice["value"] = False
            return choice["value"]
        finally:
            cv2.setMouseCallback(self.window_name, lambda *args: None)
    
    def show_confirmation_feedback(self, plots, confirmed):
        """Show a brief confirmation result overlay"""
        frame = plots.copy()
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        message = "결과 저장 (YES)" if confirmed else "결과 저장 (NO)"
        color = (0, 200, 0) if confirmed else (0, 0, 255)
        text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
        pos = ((w - text_size[0]) // 2, (h + text_size[1]) // 2)
        self._put_text(frame, message, (pos[0], pos[1]), color, 1.2, 3)
        self.show(frame)
        self.wait_key(600)
    
    def _resize_for_display(self, img):
        """Optionally scale frame before display"""
        if self.window_scale == 1.0:
            return img
        new_width = max(1, int(img.shape[1] * self.window_scale))
        new_height = max(1, int(img.shape[0] * self.window_scale))
        return cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    def show(self, img):
        """Display image"""
        self._create_window()
        display_frame = self._resize_for_display(img)
        cv2.imshow(self.window_name, display_frame)
    
    def wait_key(self, delay=1):
        """Wait for key input"""
        return cv2.waitKey(delay)
