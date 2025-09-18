from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import sequence_store


def _process_one(payload: dict) -> dict:
    # TODO: add real transforms here if needed
    processed = dict(payload)

    # TODO: Find a good place to save locally store data without github syncing it
    # sequence_store.save_data_locally(processed)
    return processed

def process(data):
    """
    If dict -> process one and return dict.
    If list[dict] -> process each and return list of dicts (same shape back).
    """
    if isinstance(data, list):
        return [_process_one(p) for p in data]
    return _process_one(data)
