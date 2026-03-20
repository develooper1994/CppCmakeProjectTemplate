#include <QApplication>
#include <QPushButton>
#include <QVBoxLayout>
#include <QWidget>
#include <QLabel>
#include "dummy_lib/greet.h"
#include "BuildInfo.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    QWidget window;
    window.setWindowTitle(QString::fromStdString(std::string(build_info::project_name)));
    window.setMinimumSize(400, 200);

    QVBoxLayout *layout = new QVBoxLayout(&window);

    QLabel *infoLabel = new QLabel(QString("Version: %1\nCompiler: %2\nArch: %3")
        .arg(build_info::project_version.data())
        .arg(build_info::compiler_id.data())
        .arg(build_info::architecture.data()));
    
    QLabel *greetLabel = new QLabel(QString::fromStdString(dummy_lib::get_greeting()));
    greetLabel->setStyleSheet("font-weight: bold; color: blue;");

    QPushButton *button = new QPushButton("Close Application");
    QObject::connect(button, &QPushButton::clicked, &app, &QApplication::quit);

    layout->addWidget(infoLabel);
    layout->addWidget(greetLabel);
    layout->addWidget(button);

    window.show();

    return app.exec();
}
