import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

class WebViewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.browser = QWebEngineView()
        self.browser.setUrl('https://www.example.com')  # Replace with your URL
        self.setCentralWidget(self.browser)
        self.showFullScreen()  # Set the window to full screen

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WebViewApp()
    window.show()
    sys.exit(app.exec_())