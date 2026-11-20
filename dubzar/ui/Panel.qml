import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property bool open: false
    signal closed()

    width: 340
    height: card.height + 32

    QtObject {
        id: dz
        readonly property color bg: "#f52b2622"
        readonly property color surface: "#352f2a"
        readonly property color hairline: "#4a423b"
        readonly property color text: "#f7f5f0"
        readonly property color muted: "#a89f94"
        readonly property color accent: "#f2c14e"
        readonly property color accentInk: "#2b2622"
        readonly property int ms: ctl.animations ? 160 : 0
    }

    component Lbl: Text {
        color: dz.muted
        font.family: ctl.sansFamily
        font.pixelSize: 12
    }

    component Hair: Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: 4
        Layout.bottomMargin: 4
        height: 1
        color: dz.hairline
    }

    component Key: Rectangle {
        property alias text: keyText.text
        implicitWidth: keyText.implicitWidth + 14
        implicitHeight: 20
        radius: 10
        color: dz.surface
        border.color: dz.hairline
        Text {
            id: keyText
            anchors.centerIn: parent
            color: dz.muted
            font.family: ctl.sansFamily
            font.pixelSize: 11
        }
    }

    component FocusRing: Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: height / 2
        color: "transparent"
        border.color: dz.accent
        border.width: 2
        visible: parent.activeFocus
    }

    component Toggle: Item {
        id: tg
        property string label
        property bool checked
        property bool available: true
        signal toggled(bool value)
        Layout.fillWidth: true
        implicitHeight: 28
        activeFocusOnTab: available
        opacity: available ? 1 : 0.45
        Accessible.role: Accessible.CheckBox
        Accessible.name: label
        Accessible.checked: checked
        Keys.onSpacePressed: if (tg.available) tg.toggled(!tg.checked)
        Text {
            text: tg.label
            color: dz.text
            font.family: ctl.sansFamily
            font.pixelSize: 13
            anchors.verticalCenter: parent.verticalCenter
        }
        Rectangle {
            id: track
            width: 32
            height: 18
            radius: 9
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            color: tg.checked ? dz.accent : dz.surface
            border.color: tg.checked ? dz.accent : dz.hairline
            Behavior on color { ColorAnimation { duration: dz.ms } }
            Rectangle {
                width: 14
                height: 14
                radius: 7
                y: 2
                x: tg.checked ? 16 : 2
                color: tg.checked ? dz.accentInk : dz.muted
                Behavior on x { NumberAnimation { duration: dz.ms; easing.type: Easing.OutCubic } }
            }
            FocusRing { anchors.margins: -3 }
        }
        MouseArea {
            anchors.fill: parent
            enabled: tg.available
            cursorShape: Qt.PointingHandCursor
            onClicked: tg.toggled(!tg.checked)
        }
    }

    component Slide: Item {
        id: sl
        property real from: 0
        property real to: 100
        property real value: 0
        property real step: 1
        signal moved(real value)
        Layout.fillWidth: true
        implicitHeight: 24
        activeFocusOnTab: true
        Accessible.role: Accessible.Slider
        readonly property real ratio: (value - from) / (to - from)
        function setFromX(x) {
            var r = Math.min(1, Math.max(0, x / width))
            moved(Math.round((from + r * (to - from)) / step) * step)
        }
        Keys.onLeftPressed: moved(Math.max(from, value - step))
        Keys.onRightPressed: moved(Math.min(to, value + step))
        Keys.onDownPressed: moved(Math.max(from, value - step))
        Keys.onUpPressed: moved(Math.min(to, value + step))
        Rectangle {
            id: rail
            height: 4
            radius: 2
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            color: dz.surface
            border.color: dz.hairline
            Rectangle {
                height: parent.height
                radius: 2
                width: parent.width * sl.ratio
                color: dz.accent
            }
        }
        Rectangle {
            width: 14
            height: 14
            radius: 7
            color: dz.accent
            x: sl.ratio * (sl.width - 14)
            anchors.verticalCenter: parent.verticalCenter
            FocusRing { anchors.margins: -3 }
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onPressed: (m) => sl.setFromX(m.x)
            onPositionChanged: (m) => { if (pressed) sl.setFromX(m.x) }
        }
    }

    component Swatches: Row {
        id: sw
        property var colors: []
        property string current
        signal picked(string color)
        spacing: 8
        Repeater {
            model: sw.colors
            delegate: Item {
                id: cell
                required property string modelData
                width: 22
                height: 22
                activeFocusOnTab: true
                Accessible.role: Accessible.Button
                Accessible.name: modelData
                Keys.onSpacePressed: sw.picked(modelData)
                Keys.onReturnPressed: sw.picked(modelData)
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: width / 2
                    color: cell.modelData
                    border.color: dz.hairline
                }
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -2
                    radius: width / 2
                    color: "transparent"
                    border.color: dz.accent
                    border.width: 2
                    visible: sw.current.toUpperCase() === cell.modelData.toUpperCase() || cell.activeFocus
                    opacity: sw.current.toUpperCase() === cell.modelData.toUpperCase() ? 1 : 0.6
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: sw.picked(cell.modelData)
                }
            }
        }
    }

    Timer {
        id: idle
        interval: ctl.idleCloseMs
        running: root.open && ctl.idleCloseMs > 0
        onTriggered: { if (hover.hovered) idle.restart(); else ctl.close() }
    }

    Connections {
        target: ctl
        function onActivity() { idle.restart() }
    }

    Item {
        id: card
        x: 16
        y: 16 + (root.open ? 0 : 8)
        width: 308
        height: col.implicitHeight + 32
        opacity: root.open ? 1 : 0
        Behavior on opacity {
            NumberAnimation {
                duration: root.open ? dz.ms : Math.round(dz.ms * 0.75)
                easing.type: Easing.OutCubic
                onRunningChanged: if (!running && !root.open) root.closed()
            }
        }
        Behavior on y { NumberAnimation { duration: dz.ms; easing.type: Easing.OutCubic } }

        HoverHandler { id: hover }

        Rectangle {
            anchors.fill: parent
            radius: 16
            color: dz.bg
            border.color: dz.hairline
        }

        FocusScope {
            anchors.fill: parent
            focus: root.open
            Keys.onEscapePressed: ctl.close()

            MouseArea {  // the header is the handle: drag it to move the panel
                objectName: "dragHandle"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 62
                cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                onPressed: ctl.dragStart()
                onPositionChanged: if (pressed) ctl.dragMove()
            }

            ColumnLayout {
                id: col
                x: 16
                y: 16
                width: parent.width - 32
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 9
                    Image {
                        id: logo
                        source: "dubzar-logo.svg"
                        sourceSize.height: 64
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        Layout.preferredHeight: 30
                        Layout.preferredWidth: Math.round(implicitWidth * 30 / Math.max(1, implicitHeight))
                        Accessible.role: Accessible.Graphic
                        Accessible.name: "Dubzar"
                    }
                    Rectangle { width: 6; height: 6; radius: 3; color: dz.accent; visible: ctl.status !== "Canlı" }
                    Lbl {  // plain "Canlı" is not shown (it said nothing useful); scan progress still is
                        objectName: "statusLabel"
                        text: ctl.status
                        visible: ctl.status !== "Canlı"
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Item { Layout.fillWidth: true; visible: ctl.status === "Canlı" }
                    Rectangle {
                        id: closeBtn
                        objectName: "closeButton"
                        implicitWidth: 24
                        implicitHeight: 24
                        radius: 12
                        color: closeMouse.containsMouse ? dz.surface : "transparent"
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: "Paneli kapat"
                        Keys.onSpacePressed: ctl.close()
                        Keys.onReturnPressed: ctl.close()
                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            color: dz.muted
                            font.pixelSize: 11
                        }
                        FocusRing {}
                        MouseArea {
                            id: closeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ctl.close()
                        }
                    }
                }

                Hair {}
                Toggle { objectName: "subtitleToggle"; label: "Altyazı"; checked: ctl.subtitlesEnabled; onToggled: (v) => ctl.setSubtitlesEnabled(v) }
                Toggle { label: ctl.dubbingAvailable ? "Dublaj" : "Dublaj · yakında"; available: ctl.dubbingAvailable; checked: ctl.dubbingEnabled; onToggled: (v) => ctl.setDubbingEnabled(v) }
                Hair {}

                Lbl { text: "Konum" }
                Item {
                    id: pad
                    objectName: "positionPad"
                    Layout.fillWidth: true
                    implicitHeight: 58
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Slider
                    Accessible.name: "Altyazı konumu"
                    Keys.onUpPressed: ctl.setVertical(ctl.vertical - 0.03)
                    Keys.onDownPressed: ctl.setVertical(ctl.vertical + 0.03)
                    readonly property real travel: height - barItem.height - 12
                    Rectangle {
                        anchors.fill: parent
                        radius: 10
                        color: dz.surface
                        border.color: dz.hairline
                    }
                    Rectangle {
                        id: barItem
                        x: parent.width * 0.16
                        width: parent.width * 0.68
                        height: 9
                        radius: 4.5
                        color: dz.accent
                        y: 6 + ctl.vertical * pad.travel
                        Behavior on y { NumberAnimation { duration: 60 } }
                    }
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -3
                        radius: 13
                        color: "transparent"
                        border.color: dz.accent
                        border.width: 2
                        visible: pad.activeFocus
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.SizeVerCursor
                        function place(my) { ctl.setVertical((my - 6 - barItem.height / 2) / pad.travel) }
                        onPressed: (m) => place(m.y)
                        onPositionChanged: (m) => { if (pressed) place(m.y) }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Lbl { text: "Boyut"; Layout.fillWidth: true }
                    Key { text: ctl.fontSize }
                }
                Slide { from: 18; to: 48; step: 1; value: ctl.fontSize; onMoved: (v) => ctl.setFontSize(v) }

                Lbl { text: "Yazı rengi"; Layout.topMargin: 4 }
                Swatches {
                    colors: ["#FFFFFF", "#FFD166", "#7EE0B0", "#7CC4FF", "#FF8FA3"]
                    current: ctl.textColor
                    onPicked: (c) => ctl.setTextColor(c)
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Lbl { text: "Arka plan"; Layout.fillWidth: true }
                    Key { text: ctl.backgroundOpacity + "%" }
                }
                Swatches {
                    colors: ["#000000", "#1A1C20", "#2B2622", "#0B1B3A"]
                    current: ctl.backgroundColor
                    onPicked: (c) => ctl.setBackgroundColor(c)
                }
                Slide { from: 0; to: 100; step: 5; value: ctl.backgroundOpacity; onMoved: (v) => ctl.setBackgroundOpacity(v) }

                Hair {}
                RowLayout {
                    Layout.fillWidth: true
                    Lbl { text: "Altyazı ekranı"; Layout.fillWidth: true }
                    Rectangle {
                        id: screenPill
                        implicitWidth: screenText.implicitWidth + 24
                        implicitHeight: 26
                        radius: 13
                        color: dz.surface
                        border.color: dz.hairline
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: "Ekran seç"
                        Keys.onSpacePressed: ctl.cycleScreen()
                        Keys.onReturnPressed: ctl.cycleScreen()
                        Text {
                            id: screenText
                            anchors.centerIn: parent
                            color: dz.text
                            font.family: ctl.sansFamily
                            font.pixelSize: 12
                            text: ctl.screen === "auto" ? "Oyunun ekranı"
                                : ctl.screen === "primary" ? "Ana ekran" : ctl.screen + ". ekran"
                        }
                        FocusRing {}
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ctl.cycleScreen()
                        }
                    }
                }


                RowLayout {
                    Layout.fillWidth: true
                    Lbl { text: "Panel ekranı"; Layout.fillWidth: true }
                    Rectangle {
                        id: panelPill
                        implicitWidth: panelText.implicitWidth + 24
                        implicitHeight: 26
                        radius: 13
                        color: dz.surface
                        border.color: dz.hairline
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: "Panel ekranını seç"
                        Keys.onSpacePressed: ctl.cyclePanelScreen()
                        Keys.onReturnPressed: ctl.cyclePanelScreen()
                        Text {
                            id: panelText
                            anchors.centerIn: parent
                            color: dz.text
                            font.family: ctl.sansFamily
                            font.pixelSize: 12
                            text: ctl.panelScreen === "other" ? "Diğer ekran"
                                : ctl.panelScreen === "auto" ? "Oyunun ekranı"
                                : ctl.panelScreen === "primary" ? "Ana ekran" : ctl.panelScreen + ". ekran"
                        }
                        FocusRing {}
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ctl.cyclePanelScreen()
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 6
                    Rectangle {
                        id: resetBtn
                        objectName: "resetButton"
                        implicitWidth: resetText.implicitWidth + 26
                        implicitHeight: 28
                        radius: 14
                        color: resetMouse.pressed ? dz.surface : "transparent"
                        border.color: dz.hairline
                        scale: resetMouse.pressed ? 0.97 : 1
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: "Varsayılana dön"
                        Keys.onSpacePressed: ctl.resetToDefaults()
                        Keys.onReturnPressed: ctl.resetToDefaults()
                        Behavior on scale { NumberAnimation { duration: 80 } }
                        Text {
                            id: resetText
                            anchors.centerIn: parent
                            text: "Varsayılana dön"
                            color: dz.text
                            font.family: ctl.sansFamily
                            font.pixelSize: 12
                        }
                        FocusRing {}
                        MouseArea {
                            id: resetMouse
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ctl.resetToDefaults()
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Lbl { text: "Kapat" }   // the panel takes no keyboard focus (the game keeps it): the hotkey or the cross closes it
                    Row {
                        spacing: 3
                        Repeater {
                            model: ctl.hotkeyParts
                            delegate: Key { required property string modelData; text: modelData }
                        }
                    }
                }

                Item {
                    objectName: "quitButton"
                    Layout.alignment: Qt.AlignRight
                    implicitWidth: quitText.implicitWidth + 8
                    implicitHeight: 22
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: "Dubzar'dan çık"
                    Keys.onSpacePressed: ctl.quitApp()
                    Keys.onReturnPressed: ctl.quitApp()
                    Text {
                        id: quitText
                        anchors.centerIn: parent
                        text: "Dubzar'dan çık"
                        color: quitMouse.containsMouse ? dz.text : dz.muted
                        font.family: ctl.sansFamily
                        font.pixelSize: 11
                        font.underline: quitMouse.containsMouse
                    }
                    FocusRing {}
                    MouseArea {
                        id: quitMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: ctl.quitApp()
                    }
                }
            }
        }
    }
}
