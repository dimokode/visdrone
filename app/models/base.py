from abc import ABC, abstractmethod
from typing import List, Dict


class BaseDetectionModel(ABC):
    id: str
    name: str

    @abstractmethod
    def predict(self, image_path: str) -> List[Dict]:
        """
        Возвращает список детекций в унифицированном формате
        """
        pass
