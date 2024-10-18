import customtkinter as ctk
from PIL import Image
import requests
import pystray
import threading
import sys
import os
import json
import base64
import webbrowser

# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Constants
CONFIG_FILE = "dahouse_config.json"
VERSION = "0.0.1"  # Versión actual de la aplicación
UPDATE_URL = "https://api.github.com/repos/zaindou/dahouse-gui/releases/latest"  # Reemplaza con la URL real de tu repositorio


class LoaderWindow(ctk.CTkToplevel):
    def __init__(self, parent, message="Cargando..."):
        super().__init__(parent)
        self.geometry("300x100")
        self.title("")
        self.resizable(False, False)
        self.configure(fg_color=parent.cget("fg_color"))

        self.label = ctk.CTkLabel(self, text=message, font=("Helvetica", 16))
        self.label.pack(pady=20)

        self.progressbar = ctk.CTkProgressBar(self, width=200)
        self.progressbar.pack(pady=10)
        self.progressbar.start()

    def update_message(self, message):
        self.label.configure(text=message)


class UserInfoWindow(ctk.CTk):
    def __init__(self, access_token):
        super().__init__()

        self.title("DAHOUSE - Información del Usuario")
        self.geometry("800x600")
        self.resizable(False, False)

        self.access_token = access_token
        self.create_widgets()
        self.load_user_info()

    def create_widgets(self):
        self.title_label = ctk.CTkLabel(
            self, text="Información del Usuario", font=("Helvetica", 24, "bold")
        )
        self.title_label.pack(pady=(20, 30))

        self.info_frame = ctk.CTkScrollableFrame(self, width=700, height=400)
        self.info_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.info_labels = {}
        fields = [
            "ID",
            "Correo Electrónico",
            "Nombre de Usuario",
            "Rol",
            "Jornada",
            "Fecha de Registro",
        ]
        for field in fields:
            frame = ctk.CTkFrame(self.info_frame)
            frame.pack(fill="x", padx=10, pady=5)

            label = ctk.CTkLabel(
                frame,
                text=f"{field}:",
                font=("Helvetica", 14, "bold"),
                width=200,
                anchor="w",
            )
            label.pack(side="left", padx=10)

            value_label = ctk.CTkLabel(
                frame, text="Cargando...", font=("Helvetica", 14), anchor="w"
            )
            value_label.pack(side="left", padx=10, fill="x", expand=True)

            self.info_labels[field] = value_label

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=20, fill="x")

        self.logout_button = ctk.CTkButton(
            self.button_frame,
            text="Cerrar Sesión",
            command=self.logout,
            width=200,
            height=40,
        )
        self.logout_button.pack(side="left", padx=20)

        self.update_button = ctk.CTkButton(
            self.button_frame,
            text="Buscar Actualizaciones",
            command=self.check_for_updates,
            width=200,
            height=40,
        )
        self.update_button.pack(side="right", padx=20)

    def load_user_info(self):
        loader = LoaderWindow(self, "Cargando información del usuario...")
        self.after(100, lambda: self._load_user_info(loader))

    def _load_user_info(self, loader):
        url = "http://127.0.0.1:5000/user"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                self.update_user_info(user_data)
            else:
                self.show_error("No se pudo obtener la información del usuario.")
        except requests.ConnectionError:
            self.show_error("No se pudo conectar al servidor.")
        finally:
            loader.destroy()

    def update_user_info(self, user_data):
        field_mapping = {
            "ID": "id",
            "Correo Electrónico": "correo_electronico",
            "Nombre de Usuario": "nombre_usuario",
            "Rol": "rol",
            "Jornada": "jornada",
            "Fecha de Registro": "fecha_registro",
        }

        for field, key in field_mapping.items():
            value = user_data.get(key, "No disponible")
            if isinstance(value, bool):
                value = "Sí" if value else "No"
            self.info_labels[field].configure(text=str(value))

    def show_error(self, message):
        for label in self.info_labels.values():
            label.configure(text="Error al cargar")
        ctk.CTkLabel(
            self, text=message, text_color="red", font=("Helvetica", 14, "bold")
        ).pack(pady=10)

    def logout(self):
        self.destroy()
        show_login_window()

    def check_for_updates(self):
        try:
            response = requests.get(UPDATE_URL)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"]
                if latest_version > VERSION:
                    self.show_update_notification(
                        latest_version, latest_release["html_url"]
                    )
                else:
                    self.show_info("Estás utilizando la última versión.")
        except requests.RequestException:
            self.show_error("No se pudo verificar actualizaciones.")

    def show_update_notification(self, new_version, download_url):
        update_window = ctk.CTkToplevel(self)
        update_window.title("Actualización Disponible")
        update_window.geometry("300x150")

        label = ctk.CTkLabel(
            update_window, text=f"Nueva versión disponible: {new_version}"
        )
        label.pack(pady=10)

        def open_download():
            webbrowser.open(download_url)
            update_window.destroy()

        download_button = ctk.CTkButton(
            update_window, text="Descargar", command=open_download
        )
        download_button.pack(pady=10)

        close_button = ctk.CTkButton(
            update_window, text="Cerrar", command=update_window.destroy
        )
        close_button.pack(pady=10)

    def show_info(self, message):
        info_window = ctk.CTkToplevel(self)
        info_window.title("Información")
        info_window.geometry("300x100")

        label = ctk.CTkLabel(info_window, text=message)
        label.pack(pady=20)

        close_button = ctk.CTkButton(
            info_window, text="Cerrar", command=info_window.destroy
        )
        close_button.pack(pady=10)


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DAHOUSE - Iniciar sesión")
        self.geometry("400x480")
        self.resizable(False, False)

        # Load and resize the logo
        self.logo_image = ctk.CTkImage(
            Image.open(resource_path("logo.png")), size=(250, 50)
        )

        self.create_widgets()
        self.load_saved_credentials()

    def create_widgets(self):
        self.logo_label = ctk.CTkLabel(self, image=self.logo_image, text="")
        self.logo_label.pack(pady=(30, 0))

        self.title_label = ctk.CTkLabel(
            self, text="Iniciar sesión", font=("Helvetica", 15, "bold")
        )
        self.title_label.pack(pady=(20))

        self.username_entry = ctk.CTkEntry(
            self, placeholder_text="Usuario", width=300, height=40
        )
        self.username_entry.pack(pady=10)

        self.password_entry = ctk.CTkEntry(
            self, placeholder_text="Contraseña", show="*", width=300, height=40
        )
        self.password_entry.pack(pady=10)

        self.remember_var = ctk.BooleanVar()
        self.remember_checkbox = ctk.CTkCheckBox(
            self, text="Recordar mis datos", variable=self.remember_var
        )
        self.remember_checkbox.pack(pady=10)

        self.login_button = ctk.CTkButton(
            self, text="Iniciar sesión", command=self.login, width=200, height=40
        )
        self.login_button.pack(pady=20)

        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.pack(pady=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.show_error("Por favor, ingresa usuario y contraseña.")
            return

        loader = LoaderWindow(self, "Iniciando sesión...")
        self.after(100, lambda: self._login(username, password, loader))

    def _login(self, username, password, loader):
        url = "http://127.0.0.1:5000/login"
        payload = {"nombre_usuario": username, "password": password}

        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if self.remember_var.get():
                    self.save_credentials(username, password)
                else:
                    self.clear_saved_credentials()
                loader.destroy()
                self.destroy()  # Close login window
                show_user_info_window(data["access_token"])
            elif response.status_code == 401:
                self.show_error("Credenciales incorrectas.")
            elif response.status_code == 404:
                self.show_error("Usuario no encontrado.")
            else:
                self.show_error("Error desconocido al iniciar sesión.")
        except requests.ConnectionError:
            self.show_error("No se pudo conectar al servidor.")
        finally:
            loader.destroy()

    def show_error(self, message):
        self.error_label.configure(text=message)

    def save_credentials(self, username, password):
        config = {
            "username": base64.b64encode(username.encode()).decode(),
            "password": base64.b64encode(password.encode()).decode(),
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

    def load_saved_credentials(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            self.username_entry.insert(
                0, base64.b64decode(config["username"].encode()).decode()
            )
            self.password_entry.insert(
                0, base64.b64decode(config["password"].encode()).decode()
            )
            self.remember_var.set(True)

    def clear_saved_credentials(self):
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)


def show_login_window():
    login_window = LoginWindow()
    login_window.mainloop()


def show_user_info_window(access_token):
    user_info_window = UserInfoWindow(access_token)
    user_info_window.mainloop()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def create_image():
    return Image.open(resource_path("logo.png"))


def create_menu(icon, item):
    if str(item) == "Abrir":
        icon.stop()
        show_login_window()
    elif str(item) == "Salir":
        icon.stop()
        os._exit(0)


# Main application logic
def run_app():
    image = create_image()
    menu = pystray.Menu(
        pystray.MenuItem("Abrir", create_menu), pystray.MenuItem("Salir", create_menu)
    )
    icon = pystray.Icon("DAHOUSE", image, "DAHOUSE", menu)
    icon.run()


if __name__ == "__main__":
    app_thread = threading.Thread(target=run_app)
    app_thread.start()
    show_login_window()
