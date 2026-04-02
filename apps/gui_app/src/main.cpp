#include <QApplication>
#include <QPushButton>
#include <QVBoxLayout>
#include <QWidget>
#include <QLabel>
#include "dummy_lib/dummy_lib.h"
#include "BuildInfo.h"

#ifdef ENABLE_QML_SUPPORT
#include <QQmlApplicationEngine>
#include <QQmlContext>
#endif

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

#ifdef ENABLE_QML_SUPPORT
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("backendGreet", QString::fromStdString(dummy_lib::get_greeting()));
    const QUrl url(QStringLiteral("qrc:/qt/qml/main.qml")); // Note: This expects a .qrc file or direct path
    // For simplicity in template, we'll try to load from local file first
    engine.load(QUrl::fromLocalFile("apps/gui_app/src/main.qml"));
    if (engine.rootObjects().isEmpty())
        return -1;
#else
    QWidget window;
    window.setWindowTitle(QString::fromStdString(std::string(gui_app_info::project_name)));
    window.setMinimumSize(400, 200);

    QVBoxLayout *layout = new QVBoxLayout(&window);

    QLabel *infoLabel = new QLabel(QString("Version: %1\nCompiler: %2\nArch: %3")
        .arg(gui_app_info::project_version.data())
        .arg(gui_app_info::compiler_id.data())
        .arg(gui_app_info::architecture.data()));
    
    QLabel *greetLabel = new QLabel(QString::fromStdString(dummy_lib::get_greeting()));
    greetLabel->setStyleSheet("font-weight: bold; color: blue;");

    QPushButton *button = new QPushButton("Close Application (Widgets)");
    QObject::connect(button, &QPushButton::clicked, &app, &QApplication::quit);

    layout->addWidget(infoLabel);
    layout->addWidget(greetLabel);
    layout->addWidget(button);

    window.show();
#endif

    return app.exec();
}
