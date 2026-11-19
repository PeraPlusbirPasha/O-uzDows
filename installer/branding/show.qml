import QtQuick 2.5

Rectangle {
    id: slide
    color: "#1c202a"
    property bool active: false
    function onActivate() { active = true }
    function onLeave() { active = false }
    Column {
        anchors.centerIn: parent
        width: parent.width * 0.84
        spacing: 18
        Rectangle {
            width: 144; height: 144; radius: 16
            color: "white"
            anchors.horizontalCenter: parent.horizontalCenter
            Image {
                id: cat
                anchors.fill: parent
                anchors.margins: 6
                source: "file:///usr/share/oguzdows/rifki/idle.png"
                fillMode: Image.PreserveAspectFit
                sourceSize.width: 144
                sourceSize.height: 144
            }
        }
        Text {
            width: parent.width
            text: "Rıfkı yanında."
            color: "#fff9ef"
            font.pixelSize: 28
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "OğuzDows bilgisayarına yerleşiyor.\nDiskini ve gücü bağlı tut. Gerçek ilerlemeyi kurucudan izle.\n\nRıfkı yalnızca istersen açılır; kurulumda sakin kalır.\nKurulum bittiğinde açık bir sonuç ekranı göreceksin."
            color: "#c3c9d4"
            font.pixelSize: 15
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: 64; height: 3
            color: "#3fc5c1"
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
