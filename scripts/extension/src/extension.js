const vscode = require('vscode');
const fs     = require('fs');
const path   = require('path');

// Proje adı rename'inden muaf dosya/dizin isimleri (tam eşleşme, küçük harf)
const LICENSE_NAMES = new Set([
    'license', 'licence', 'copying', 'copyright', 'notice',
    'license.txt', 'licence.txt', 'license.md', 'licence.md',
]);

// Rename uygulanmayacak binary uzantılar
const BINARY_EXTS = new Set([
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.bmp', '.webp',
    '.bin', '.hex', '.a', '.so', '.lib', '.dll', '.exe',
    '.zip', '.tar', '.gz', '.7z', '.pdf',
]);

const OLD_NAME = 'CppCmakeProjectTemplate';

function isBinary(filePath) {
    return BINARY_EXTS.has(path.extname(filePath).toLowerCase());
}

function isLicense(filePath) {
    return LICENSE_NAMES.has(path.basename(filePath).toLowerCase());
}

/** Dizini özyinelemeli kopyalar; text dosyalarda projectName rename uygular */
function copyDir(src, dst, projectName) {
    fs.mkdirSync(dst, { recursive: true });

    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
        const srcPath = path.join(src, entry.name);
        const dstName = entry.name.includes(OLD_NAME)
            ? entry.name.replace(OLD_NAME, projectName)
            : entry.name;
        const dstPath = path.join(dst, dstName);

        if (entry.isDirectory()) {
            copyDir(srcPath, dstPath, projectName);
        } else {
            if (isBinary(srcPath) || isLicense(srcPath)) {
                // Ham kopyala
                fs.copyFileSync(srcPath, dstPath);
            } else {
                // Text: içerikte rename uygula
                let content = fs.readFileSync(srcPath, 'utf8');
                if (content.includes(OLD_NAME)) {
                    content = content.split(OLD_NAME).join(projectName);
                }
                fs.writeFileSync(dstPath, content, 'utf8');
            }
        }
    }
}

function activate(context) {
    const disposable = vscode.commands.registerCommand(
        'cpp-cmake-scaffolder.init',
        async () => {
            // 1. Hedef klasörü seç
            const picked = await vscode.window.showOpenDialog({
                canSelectFiles:   false,
                canSelectFolders: true,
                openLabel:        'Projeyi Oluştur',
            });
            if (!picked || picked.length === 0) return;
            const targetDir = picked[0].fsPath;

            // 2. Proje adını al
            const projectName = await vscode.window.showInputBox({
                prompt:        'Proje adı (CMake uyumlu: harf/rakam/alt çizgi)',
                value:         path.basename(targetDir),
                validateInput: v =>
                    /^[A-Za-z_][A-Za-z0-9_]*$/.test(v) ? null : 'Geçersiz isim',
            });
            if (!projectName) return;

            // 3. templates/ → targetDir kopyala + rename
            const templateDir = path.join(context.extensionPath, 'templates');

            try {
                copyDir(templateDir, targetDir, projectName);

                const count = fs.readdirSync(targetDir).length;
                vscode.window.showInformationMessage(
                    `✅ "${projectName}" oluşturuldu.`
                );

                // 4. Yeni pencerede aç
                await vscode.commands.executeCommand(
                    'vscode.openFolder',
                    vscode.Uri.file(targetDir),
                    { forceNewWindow: true }
                );
            } catch (err) {
                vscode.window.showErrorMessage(`Hata: ${err.message}`);
            }
        }
    );

    context.subscriptions.push(disposable);
}

exports.activate = activate;
