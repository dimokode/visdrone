class ModelRegistry:
    _models = {}

    @classmethod
    def register(cls, model):
        cls._models[model.id] = model

    @classmethod
    def get(cls, model_id):
        return cls._models.get(model_id)

    @classmethod
    def list(cls):
        return cls._models.values()
