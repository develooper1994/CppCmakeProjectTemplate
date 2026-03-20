import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 400
    height: 300
    title: "Project Metadata (QML)"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 10

        Text {
            text: "Hello from QML!"
            font.pixelSize: 24
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: "Backend Greeting: " + backendGreet
            font.italic: true
            Layout.alignment: Qt.AlignHCenter
        }

        Button {
            text: "Close"
            onClicked: Qt.quit()
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
