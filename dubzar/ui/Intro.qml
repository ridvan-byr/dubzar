import QtQuick

Item {
    id: root
    property real dP: 0   // the D appearing
    property real wP: 0   // the letters sliding out (and the D gliding to its place)
    property real fP: 0   // the letters fading in
    property real hP: 0   // the hint line fading in
    property real cP: 0   // the whole card
    readonly property var curve: [0.2, 0.8, 0.2, 1, 1, 1]
    readonly property real logoH: 88
    readonly property real k: logoH / 264          // pixels per logo unit (the D is 264 units tall)
    readonly property real xc: 175 * k             // letters are visible right of the pip's hole only

    function ms(v) { return Math.max(1, Math.round(v * intro.timeScale)) }

    function start() {
        seq.stop()
        holdTimer.stop()
        dP = 0; wP = 0; fP = 0; hP = 0; cP = 0
        if (intro.animations) {
            seq.start()
        } else {
            dP = 1; wP = 1; fP = 1; hP = 1; cP = 1
            holdTimer.interval = ms(intro.holdMs)
            holdTimer.start()
        }
    }

    function stop() {
        seq.stop()
        holdTimer.stop()
    }

    width: 380
    height: card.height + 32

    QtObject {
        id: dz
        readonly property color bg: "#f52b2622"
        readonly property color surface: "#352f2a"
        readonly property color hairline: "#4a423b"
        readonly property color muted: "#a89f94"
    }

    Timer {
        id: holdTimer
        onTriggered: intro.finish()
    }

    SequentialAnimation {
        id: seq
        ParallelAnimation {
            NumberAnimation { target: root; property: "cP"; to: 1; duration: root.ms(160); easing.type: Easing.OutCubic }
            NumberAnimation {
                target: root; property: "dP"; to: 1; duration: root.ms(360)
                easing.type: Easing.BezierSpline; easing.bezierCurve: root.curve
            }
            SequentialAnimation {
                PauseAnimation { duration: root.ms(520) }
                ParallelAnimation {
                    NumberAnimation {
                        target: root; property: "wP"; to: 1; duration: root.ms(720)
                        easing.type: Easing.BezierSpline; easing.bezierCurve: root.curve
                    }
                    NumberAnimation { target: root; property: "fP"; to: 1; duration: root.ms(280) }
                }
            }
        }
        PauseAnimation { duration: root.ms(150) }
        NumberAnimation { target: root; property: "hP"; to: 1; duration: root.ms(240); easing.type: Easing.OutCubic }
        PauseAnimation { duration: root.ms(intro.holdMs) }
        NumberAnimation { target: root; property: "cP"; to: 0; duration: root.ms(400); easing.type: Easing.InOutQuad }
        ScriptAction { script: intro.finish() }
    }

    Rectangle {
        id: card
        x: 16
        y: 16
        width: 348
        height: col.implicitHeight + 40
        radius: 20
        color: dz.bg
        border.color: dz.hairline
        opacity: root.cP

        Column {
            id: col
            y: 20
            spacing: 14
            anchors.horizontalCenter: parent.horizontalCenter

            Item {
                id: logoBox
                width: dImg.width
                height: root.logoH
                anchors.horizontalCenter: parent.horizontalCenter

                Item {
                    id: lead
                    width: logoBox.width
                    height: logoBox.height
                    // the D starts in the middle of the card and glides left while the letters open
                    x: (logoBox.width / 2 - 116 * root.k) * (1 - root.wP)

                    Item {
                        id: clipBox
                        x: root.xc
                        width: lead.width - root.xc
                        height: lead.height
                        clip: true

                        Image {
                            id: wordImg
                            source: "dubzar-logo-word.svg"
                            sourceSize.height: root.logoH * 2
                            height: root.logoH
                            width: implicitWidth * root.logoH / Math.max(1, implicitHeight)
                            readonly property real slide: width - root.xc + 24 * root.k
                            x: -root.xc - slide * (1 - root.wP)
                            opacity: root.fP
                        }
                    }

                    Image {
                        id: dImg
                        source: "dubzar-logo-d.svg"
                        sourceSize.height: root.logoH * 2
                        height: root.logoH
                        width: implicitWidth * root.logoH / Math.max(1, implicitHeight)
                        opacity: root.dP
                        scale: 0.88 + 0.12 * root.dP
                    }
                }
            }

            Row {
                id: hintRow
                spacing: 6
                anchors.horizontalCenter: parent.horizontalCenter
                opacity: root.hP

                Repeater {
                    model: intro.keys
                    delegate: Rectangle {
                        required property string modelData
                        width: keyText.implicitWidth + 14
                        height: 20
                        radius: 10
                        color: dz.surface
                        border.color: dz.hairline
                        Text {
                            id: keyText
                            anchors.centerIn: parent
                            text: parent.modelData
                            color: dz.muted
                            font.family: intro.sansFamily
                            font.pixelSize: 11
                        }
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: intro.message
                    color: dz.muted
                    font.family: intro.sansFamily
                    font.pixelSize: 13
                }
            }
        }
    }
}
