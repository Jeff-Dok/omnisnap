import pytest
import customtkinter as ctk


@pytest.fixture(scope="module")
def ctk_root():
    root = ctk.CTk()
    root.withdraw()
    yield root
    root.destroy()
