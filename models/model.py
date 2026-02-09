import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torchvision.models import mobilenet_v2


def calculate_iou_torch(boxes1, boxes2):
    """
    Вычисляет IoU между двумя наборами bounding boxes (PyTorch версия)
    """
    # Определяем координаты пересечения
    x1 = torch.max(boxes1[:, 0].unsqueeze(1), boxes2[:, 0].unsqueeze(0))
    y1 = torch.max(boxes1[:, 1].unsqueeze(1), boxes2[:, 1].unsqueeze(0))
    x2 = torch.min(boxes1[:, 2].unsqueeze(1), boxes2[:, 2].unsqueeze(0))
    y2 = torch.min(boxes1[:, 3].unsqueeze(1), boxes2[:, 3].unsqueeze(0))
    
    # Площадь пересечения
    inter = torch.clamp(x2 - x1, min=0) * torch.clamp(y2 - y1, min=0)
    
    # Площади боксов
    area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
    area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])
    
    # IoU
    union = area1.unsqueeze(1) + area2.unsqueeze(0) - inter
    iou = inter / (union + 1e-8)
    
    return iou



class VisDroneSSD(nn.Module):
    def __init__(self, num_real_classes=None, img_size=1024):
        super().__init__()
        self.num_real_classes = num_real_classes
        self.num_total_classes = num_real_classes + 1
        self.img_size = img_size
        
        print(f"\n=== Создание модели для VisDrone ===")
        print(f"Анализ данных: объекты {1.5}px - {556.4}px по ширине")
        print(f"Медианный размер: {20.8}x{29.4}px")
        
        # MobileNetV2 backbone
        weights = torchvision.models.MobileNet_V2_Weights.DEFAULT
        mobilenet = mobilenet_v2(weights=weights)
        
        # 4 уровня feature maps (для лучшего покрытия)
        self.layer1 = nn.Sequential(*list(mobilenet.features[:7]))   # 128x128
        self.layer2 = nn.Sequential(*list(mobilenet.features[7:14])) # 64x64
        self.layer3 = nn.Sequential(*list(mobilenet.features[14:]))  # 32x32
        
        # ДОБАВЛЯЕМ ДОПОЛНИТЕЛЬНЫЙ УРОВЕНЬ ДЛЯ ОЧЕНЬ БОЛЬШИХ ОБЪЕКТОВ
        self.layer4 = nn.Sequential(
            nn.Conv2d(1280, 512, kernel_size=3, padding=1, stride=2),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
        )
        
        # Определяем размеры
        with torch.no_grad():
            dummy = torch.zeros(1, 3, img_size, img_size)
            f1 = self.layer1(dummy)  # 128x128
            f2 = self.layer2(f1)     # 64x64
            f3 = self.layer3(f2)     # 32x32
            f4 = self.layer4(f3)     # 16x16
            
            f1_h, f1_w = f1.shape[2], f1.shape[3]
            f2_h, f2_w = f2.shape[2], f2.shape[3]
            f3_h, f3_w = f3.shape[2], f3.shape[3]
            f4_h, f4_w = f4.shape[2], f4.shape[3]
            
            print(f"\nРазмеры feature maps:")
            print(f"  Level1: {f1_h}x{f1_w} - для очень мелких объектов (1-50px)")
            print(f"  Level2: {f2_h}x{f2_w} - для мелких/средних (20-100px)")
            print(f"  Level3: {f3_h}x{f3_w} - для средних/крупных (80-250px)")
            print(f"  Level4: {f4_h}x{f4_w} - для очень крупных (200-600px)")
        
        # ОПТИМИЗИРОВАННЫЕ ANCHORS НА ОСНОВЕ АНАЛИЗА ДАННЫХ
        self.feature_maps_info = [
            {  # Level1: 128x128 - ОЧЕНЬ МЕЛКИЕ объекты (1-50px)
                'size': (f1_h, f1_w), 
                'channels': f1.shape[1], 
                'num_anchors': 5,
                'sizes_px': [
                    (3, 4),     # очень маленькие (ближние точки)
                    (8, 12),    # маленькие
                    (15, 20),   # мелкие объекты
                    (25, 35),   # средние-мелкие
                    (40, 55),   # переход к уровню 2
                ]
            },
            {  # Level2: 64x64 - МЕЛКИЕ/СРЕДНИЕ объекты (20-100px)
                'size': (f2_h, f2_w), 
                'channels': f2.shape[1], 
                'num_anchors': 5,
                'sizes_px': [
                    (30, 40),   # типичные car (медианные)
                    (45, 60),   # средние
                    (60, 80),   # крупные car / мелкие van
                    (75, 100),  # средние van
                    (90, 120),  # переход к уровню 3
                ]
            },
            {  # Level3: 32x32 - СРЕДНИЕ/КРУПНЫЕ объекты (80-250px)
                'size': (f3_h, f3_w), 
                'channels': f3.shape[1], 
                'num_anchors': 6,  # больше anchors для больших объектов
                'sizes_px': [
                    (80, 110),   # средние объекты
                    (100, 140),  # крупные
                    (130, 170),  # очень крупные
                    (160, 210),  # большие грузовики
                    (200, 260),  # очень большие
                    (240, 310),  # переход к уровню 4
                ]
            },
            {  # Level4: 16x16 - ОЧЕНЬ КРУПНЫЕ объекты (200-600px)
                'size': (f4_h, f4_w), 
                'channels': f4.shape[1], 
                'num_anchors': 5,
                'sizes_px': [
                    (200, 250),   # нижняя граница больших объектов
                    (250, 320),   # средние-большие
                    (300, 380),   # большие
                    (350, 450),   # очень большие
                    (450, 550),   # максимальные из датасета
                ]
            },
        ]
        
        # Создаем default boxes
        self.default_boxes = self._generate_default_boxes_visdrone()
        
        # Heads
        self.loc_heads = nn.ModuleList()
        self.cls_heads = nn.ModuleList()
        
        for info in self.feature_maps_info:
            loc_out_channels = info['num_anchors'] * 4
            cls_out_channels = info['num_anchors'] * self.num_total_classes
            
            self.loc_heads.append(
                nn.Conv2d(info['channels'], loc_out_channels, kernel_size=3, padding=1)
            )
            self.cls_heads.append(
                nn.Conv2d(info['channels'], cls_out_channels, kernel_size=3, padding=1)
            )
        
        self._init_weights()
        self._verify_setup()
    
    def _generate_default_boxes_visdrone(self):
        """Генерация anchors оптимизированных для VisDrone"""
        boxes = []
        
        print("\n=== Генерация anchors для VisDrone ===")
        print("Учитывая диапазон объектов: 2px - 588px")
        
        total_anchors_per_level = []
        
        for level_idx, info in enumerate(self.feature_maps_info):
            f_h, f_w = info['size']
            num_anchors = info['num_anchors']
            
            step_x = 1.0 / f_w
            step_y = 1.0 / f_h
            
            level_anchors = 0
            
            for i in range(f_h):
                for j in range(f_w):
                    cx = (j + 0.5) * step_x
                    cy = (i + 0.5) * step_y
                    
                    for anchor_idx in range(num_anchors):
                        w_px, h_px = info['sizes_px'][anchor_idx]
                        
                        # НОРМАЛИЗАЦИЯ К IMG_SIZE
                        w = w_px / self.img_size
                        h = h_px / self.img_size
                        
                        boxes.append([
                            max(0.0, cx - w/2),
                            max(0.0, cy - h/2),
                            min(1.0, cx + w/2),
                            min(1.0, cy + h/2)
                        ])
                        level_anchors += 1
            
            total_anchors_per_level.append(level_anchors)
            print(f"Уровень {level_idx} ({f_h}x{f_w}): {num_anchors} типов, всего {level_anchors} anchors")
            for size in info['sizes_px']:
                print(f"  - {size[0]}x{size[1]}px")
        
        boxes_tensor = torch.tensor(boxes)
        
        # Анализ покрытия
        sizes_px = (boxes_tensor[:, 2:] - boxes_tensor[:, :2]) * self.img_size
        
        print(f"\nИтого anchors: {len(boxes_tensor)}")
        print(f"Покрытие размеров: {sizes_px[:, 0].min():.1f} - {sizes_px[:, 0].max():.1f}px по ширине")
        print(f"                   {sizes_px[:, 1].min():.1f} - {sizes_px[:, 1].max():.1f}px по высоте")
        
        # Проверяем покрытие максимальных размеров
        max_width_coverage = sizes_px[:, 0].max() / 556.4  # максимальная ширина из данных
        max_height_coverage = sizes_px[:, 1].max() / 587.6  # максимальная высота из данных
        
        print(f"Покрытие максимальных размеров: {max_width_coverage*100:.1f}% по ширине, "
              f"{max_height_coverage*100:.1f}% по высоте")
        
        if max_width_coverage < 0.9 or max_height_coverage < 0.9:
            print("⚠ Предупреждение: anchors не покрывают максимальные размеры объектов!")
            print("  Добавьте еще более крупные anchors на Level4")
        
        return boxes_tensor

    
    def _verify_setup(self):
        """Проверка корректности настройки"""
        total_preds = sum(info['size'][0] * info['size'][1] * info['num_anchors'] 
                         for info in self.feature_maps_info)
        
        print(f"\n=== Проверка ===")
        print(f"Predictions: {total_preds}")
        print(f"Default boxes: {len(self.default_boxes)}")
        print(f"Реальные классы: {self.num_real_classes}")
        print(f"Всего классов в модели: {self.num_total_classes}")
        
        if total_preds != len(self.default_boxes):
            print("⚠ Корректируем default boxes...")
            self._adjust_default_boxes(total_preds)
    
    def _adjust_default_boxes(self, target_num):
        """Корректирует количество default boxes"""
        current = self.default_boxes
        
        if target_num <= len(current):
            self.default_boxes = current[:target_num]
        else:
            repeat = (target_num + len(current) - 1) // len(current)
            self.default_boxes = torch.cat([current] * repeat, dim=0)[:target_num]
    
    def _init_weights(self):
        for layer in self.loc_heads:
            nn.init.normal_(layer.weight, mean=0, std=0.01)
            nn.init.zeros_(layer.bias)
        
        for layer in self.cls_heads:
            nn.init.normal_(layer.weight, mean=0, std=0.01)
            nn.init.zeros_(layer.bias)
    
    def forward(self, x):
        """Forward pass - остаётся таким же"""
        batch_size = x.size(0)
        
        f1 = self.layer1(x)
        f2 = self.layer2(f1)
        f3 = self.layer3(f2)
        f4 = self.layer4(f3)
        
        feature_maps = [f1, f2, f3, f4]
        
        loc_preds_list = []
        cls_preds_list = []
        
        for fm, loc_head, cls_head in zip(feature_maps, self.loc_heads, self.cls_heads):
            loc_pred = loc_head(fm)
            cls_pred = cls_head(fm)
            
            batch, loc_channels, h, w = loc_pred.shape
            num_anchors = loc_channels // 4
            
            loc_pred = loc_pred.view(batch, num_anchors, 4, h, w)
            loc_pred = loc_pred.permute(0, 3, 4, 1, 2).contiguous()
            loc_pred = loc_pred.view(batch, -1, 4)
            
            # ВАЖНО: self.num_total_classes (реальные + фон)
            cls_pred = cls_pred.view(batch, num_anchors, self.num_total_classes, h, w)
            cls_pred = cls_pred.permute(0, 3, 4, 1, 2).contiguous()
            cls_pred = cls_pred.view(batch, -1, self.num_total_classes)
            
            loc_preds_list.append(loc_pred)
            cls_preds_list.append(cls_pred)
        
        loc_preds = torch.cat(loc_preds_list, dim=1)
        cls_preds = torch.cat(cls_preds_list, dim=1)
        
        if self.default_boxes.device != x.device:
            self.default_boxes = self.default_boxes.to(x.device)
        
        return loc_preds, cls_preds
    
    def decode_predictions(self, loc_preds, cls_preds, confidence_threshold=0.5, nms_threshold=0.45):
        """
        ИСПРАВЛЕННЫЙ decode для num_real_classes
        """
        device = loc_preds.device
        
        # Проверка размеров
        if loc_preds.shape[0] != len(self.default_boxes):
            min_len = min(loc_preds.shape[0], len(self.default_boxes))
            loc_preds = loc_preds[:min_len]
            cls_preds = cls_preds[:min_len]
        
        # Softmax по классам (включая фон)
        cls_probs = torch.softmax(cls_preds, dim=1)  # [anchors, num_total_classes]
        
        # Игнорируем фон (класс 0)
        # cls_probs shape: [anchors, num_total_classes]
        # Мы берем только реальные классы (1...num_real_classes)
        cls_probs_real = cls_probs[:, 1:1+self.num_real_classes]  # [anchors, num_real_classes]
        
        # Находим максимальную вероятность и класс
        confidences, class_ids = torch.max(cls_probs_real, dim=1)
        
        # class_ids теперь 0...num_real_classes-1
        # Конвертируем в оригинальные индексы 1...num_real_classes
        class_ids = class_ids + 1
        
        # Фильтруем по confidence
        mask = confidences > confidence_threshold
        
        if not mask.any():
            return []
        
        # Применяем маску
        filtered_loc_preds = loc_preds[mask]
        filtered_class_ids = class_ids[mask]
        filtered_confidences = confidences[mask]
        
        # Берём соответствующие default boxes
        mask_indices = torch.where(mask)[0].cpu()
        filtered_default_boxes = self.default_boxes[mask_indices].to(device)
        
        # Декодируем боксы
        decoded_boxes = self.decode_bbox(filtered_default_boxes, filtered_loc_preds)
        
        # NMS по классам
        final_predictions = []
        unique_classes = torch.unique(filtered_class_ids)
        
        for cls in unique_classes:
            cls_mask = filtered_class_ids == cls
            if not cls_mask.any():
                continue
            
            cls_boxes = decoded_boxes[cls_mask]
            cls_confidences = filtered_confidences[cls_mask]
            
            keep_indices = self.nms(cls_boxes, cls_confidences, nms_threshold)
            
            for idx in keep_indices:
                final_predictions.append((
                    cls_boxes[idx].cpu(),
                    int(cls),  # 1 или 2
                    cls_confidences[idx].item()
                ))
        
        final_predictions.sort(key=lambda x: x[2], reverse=True)
        return final_predictions
    
    def decode_bbox(self, default_boxes, loc_preds):
        """Декодирование боксов (оставляем как есть)"""
        default_cx = (default_boxes[:, 0] + default_boxes[:, 2]) / 2
        default_cy = (default_boxes[:, 1] + default_boxes[:, 3]) / 2
        default_w = default_boxes[:, 2] - default_boxes[:, 0]
        default_h = default_boxes[:, 3] - default_boxes[:, 1]
        
        pred_cx = loc_preds[:, 0] * default_w + default_cx
        pred_cy = loc_preds[:, 1] * default_h + default_cy
        pred_w = torch.exp(loc_preds[:, 2]) * default_w
        pred_h = torch.exp(loc_preds[:, 3]) * default_h
        
        pred_xmin = pred_cx - pred_w / 2
        pred_ymin = pred_cy - pred_h / 2
        pred_xmax = pred_cx + pred_w / 2
        pred_ymax = pred_cy + pred_h / 2
        
        pred_xmin = torch.clamp(pred_xmin, 0.0, 1.0)
        pred_ymin = torch.clamp(pred_ymin, 0.0, 1.0)
        pred_xmax = torch.clamp(pred_xmax, 0.0, 1.0)
        pred_ymax = torch.clamp(pred_ymax, 0.0, 1.0)
        
        return torch.stack([pred_xmin, pred_ymin, pred_xmax, pred_ymax], dim=1)
    
    @staticmethod
    def calculate_iou(boxes1, boxes2):
        """IoU calculation (оставляем как есть)"""
        x1 = torch.max(boxes1[:, 0].unsqueeze(1), boxes2[:, 0].unsqueeze(0))
        y1 = torch.max(boxes1[:, 1].unsqueeze(1), boxes2[:, 1].unsqueeze(0))
        x2 = torch.min(boxes1[:, 2].unsqueeze(1), boxes2[:, 2].unsqueeze(0))
        y2 = torch.min(boxes1[:, 3].unsqueeze(1), boxes2[:, 3].unsqueeze(0))
        
        inter = torch.clamp(x2 - x1, min=0) * torch.clamp(y2 - y1, min=0)
        
        area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
        area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])
        
        union = area1.unsqueeze(1) + area2.unsqueeze(0) - inter
        return inter / (union + 1e-8)
    
    @staticmethod
    def nms(boxes, scores, threshold=0.5):
        """NMS (оставляем как есть)"""
        if len(boxes) == 0:
            return []
        
        sorted_indices = torch.argsort(scores, descending=True)
        boxes = boxes[sorted_indices]
        scores = scores[sorted_indices]
        
        keep = []
        while len(boxes) > 0:
            keep.append(sorted_indices[0].item())
            if len(boxes) == 1:
                break
            
            ious = VisDroneSSD.calculate_iou(boxes[0:1], boxes[1:]).squeeze()
            mask = ious <= threshold
            boxes = boxes[1:][mask]
            scores = scores[1:][mask]
            sorted_indices = sorted_indices[1:][mask]
        
        return keep
