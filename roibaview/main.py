import sys
from PyQt6.QtWidgets import QApplication

print("Top-level import: before MainWindow")

try:
    from roibaview.gui import MainWindow
    print("Imported MainWindow")
except Exception as e:
    print("Failed to import MainWindow:", e)

try:
    from roibaview.controller import Controller
    print("Imported Controller")
except Exception as e:
    print("Failed to import Controller:", e)

def main():
    print("RoiBaView is starting...")
    app = QApplication(sys.argv)
    screen = app.primaryScreen().availableGeometry()
    window = MainWindow(screen)
    Controller(gui=window)
    window.show()
    app.exec()

# import sys
# from PyQt6.QtWidgets import QApplication
# from roibaview.gui import MainWindow
# from roibaview.controller import Controller
#
#
# def main():
#     print("RoiBaView is starting...")
#     # Start Qt Application
#     app = QApplication(sys.argv)
#     screen = app.primaryScreen().availableGeometry()
#
#     # GUI
#     window = MainWindow(screen)
#
#     # Start Controller
#     Controller(gui=window)
#     window.show()
#     app.exec()
#
#
# if __name__ == '__main__':
#     main()
