const vscode = require('vscode');
const fs = require('fs-extra');
const path = require('path');
const { exec } = require('child_process');

function activate(context) {
    let disposable = vscode.commands.registerCommand('cpp-cmake-scaffolder.init', async () => {
        const dest = await vscode.window.showOpenDialog({ 
            canSelectFiles: false, 
            canSelectFolders: true, 
            openLabel: "Projeyi başlat" 
        });

        if (!dest || dest.length === 0) return;
        const targetDir = dest[0].fsPath;

        const templateSource = path.join(context.extensionPath, 'templates');
        
        // Template kopyalama
        fs.copySync(templateSource, targetDir);

        // İsimlendirme scriptini çalıştırma
        const projectName = path.basename(targetDir);
        exec(`python3 "${path.join(targetDir, 'scripts/init_project.py')}" --name ${projectName}`, (err) => {
            if (err) {
                vscode.window.showErrorMessage("Template isimlendirme hatası!");
                return;
            }
            vscode.window.showInformationMessage("Proje başarıyla oluşturuldu!");
        });
    });
    context.subscriptions.push(disposable);
}
exports.activate = activate;
