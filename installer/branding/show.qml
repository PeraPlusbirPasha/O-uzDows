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
            text: "OğuzDows bilgisayarına yerleşiyor.\nDiskini ve gücü bağlı tut. Gerçek ilerlemeyi kurucudan izle.\n\nTakıldığında Rıfkı penceresine yazabilirsin.\nKurulum bittiğinde açık bir sonuç ekranı göreceksin."
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
    Timer {
        interval: 4600; repeat: true; running: slide.active && slide.visible
        onTriggered: {
            cat.source = "file:///usr/share/oguzdows/rifki/blink.png"
            openEyes.restart()
        }
    }
    Timer {
        id: openEyes
        interval: 180
        onTriggered: cat.source = "file:///usr/share/oguzdows/rifki/idle.png"
    }
}
