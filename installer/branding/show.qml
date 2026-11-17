import QtQuick 2.5

Rectangle {
    color: "#1c202a"
    function onActivate() {}
    function onLeave() {}
    Column {
        anchors.centerIn: parent
        width: parent.width * 0.84
        spacing: 24
        Image {
            source: "logo.png"
            width: 84; height: 84
            anchors.horizontalCenter: parent.horizontalCenter
            fillMode: Image.PreserveAspectFit
        }
        Text {
            width: parent.width
            text: "Köklerinden güç alır."
            color: "#fff9ef"
            font.pixelSize: 28
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "OğuzDows bilgisayarına yerleşiyor.\nTürkçe masaüstün, uygulamaların ve donanım araçların birazdan hazır."
            color: "#b6bac7"
            font.pixelSize: 16
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
