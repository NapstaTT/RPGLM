from backend.storage import append_to_tmp, read_tmp, clear_tmp

append_to_tmp("default", {"ver": 1, "role": "user", "content": "Привет"})
print(read_tmp("default"))  # должно вывести список с одним словарём
clear_tmp("default")
print(read_tmp("default"))  # пустой список