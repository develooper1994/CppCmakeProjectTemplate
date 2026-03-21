const vscode = require('vscode');
const fs     = require('fs');
const path   = require('path');
const cp     = require('child_process');

// ─── Rename helpers ───────────────────────────────────────────────────────────

const LICENSE_NAMES = new Set([
    'license', 'licence', 'copying', 'copyright', 'notice',
    'license.txt', 'licence.txt', 'license.md', 'licence.md',
]);

const BINARY_EXTS = new Set([
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.bmp', '.webp',
    '.bin', '.hex', '.a', '.so', '.lib', '.dll', '.exe',
    '.zip', '.tar', '.gz', '.7z', '.pdf',
]);

const OLD_NAME = 'CppCmakeProjectTemplate';

function isBinary(filePath)  { return BINARY_EXTS.has(path.extname(filePath).toLowerCase()); }
function isLicense(filePath) { return LICENSE_NAMES.has(path.basename(filePath).toLowerCase()); }

function copyDir(src, dst, projectName) {
    fs.mkdirSync(dst, { recursive: true });
    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
        const srcPath = path.join(src, entry.name);
        const dstName = entry.name.includes(OLD_NAME)
            ? entry.name.replace(OLD_NAME, projectName) : entry.name;
        const dstPath = path.join(dst, dstName);

        if (entry.isDirectory()) {
            copyDir(srcPath, dstPath, projectName);
        } else if (isBinary(srcPath) || isLicense(srcPath)) {
            fs.copyFileSync(srcPath, dstPath);
        } else {
            let content = fs.readFileSync(srcPath, 'utf8');
            if (content.includes(OLD_NAME))
                content = content.split(OLD_NAME).join(projectName);
            fs.writeFileSync(dstPath, content, 'utf8');
        }
    }
}

// ─── libtool runner ───────────────────────────────────────────────────────────

function getWorkspaceRoot() {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? null;
}

function runLibtool(workspaceRoot, args) {
    const script = path.join(workspaceRoot, 'scripts', 'libtool.py');
    if (!fs.existsSync(script)) {
        vscode.window.showErrorMessage(
            'libtool.py not found. Is this a CppCmakeProjectTemplate project?'
        );
        return;
    }
    const terminal = vscode.window.createTerminal({
        name: 'libtool',
        cwd: workspaceRoot,
    });
    terminal.show();
    terminal.sendText(`python3 "${script}" ${args}`);
}

// ─── libtool UI ───────────────────────────────────────────────────────────────

async function libtoolUI() {
    const root = getWorkspaceRoot();
    if (!root) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }

    const OP_ITEMS = [
        { label: '$(add)    add',    description: 'Create a new library skeleton',         op: 'add'    },
        { label: '$(trash)  remove', description: 'Detach or delete a library',            op: 'remove' },
        { label: '$(edit)   rename', description: 'Rename a library (all references)',     op: 'rename' },
        { label: '$(arrow-right) move', description: 'Move library to new location/subdir', op: 'move'  },
        { label: '$(link)   deps',   description: 'Add or remove library dependencies',    op: 'deps'   },
        { label: '$(list-unordered) list', description: 'List all libraries',              op: 'list'   },
        { label: '$(type-hierarchy) tree', description: 'Show ASCII dependency tree',      op: 'tree'   },
        { label: '$(check)  doctor', description: 'Check project consistency',             op: 'doctor' },
    ];

    const picked = await vscode.window.showQuickPick(OP_ITEMS, {
        placeHolder: 'libtool: select operation',
        matchOnDescription: true,
    });
    if (!picked) return;

    const op = picked.op;
    let argStr = '';

    switch (op) {

        case 'add': {
            const name = await vscode.window.showInputBox({
                prompt: 'Library name (lowercase, underscores)',
                validateInput: v => /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Invalid name',
            });
            if (!name) return;

            const version = await vscode.window.showInputBox({
                prompt: 'Version', value: '1.0.0',
            });

            const depsRaw = await vscode.window.showInputBox({
                prompt: 'Dependencies (comma-separated, leave blank for none)', value: '',
            });

            const linkPick = await vscode.window.showQuickPick(['yes', 'no'], {
                placeHolder: 'Link to apps/main_app?',
            });

            argStr = name;
            if (version && version !== '1.0.0') argStr += ` --version ${version}`;
            if (depsRaw && depsRaw.trim())       argStr += ` --deps ${depsRaw.trim()}`;
            if (linkPick === 'yes')               argStr += ' --link-app';
            break;
        }

        case 'remove': {
            const name = await vscode.window.showInputBox({
                prompt: 'Library name to remove',
                validateInput: v => /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Invalid name',
            });
            if (!name) return;

            const delPick = await vscode.window.showQuickPick(
                ['keep files (detach only)', 'delete files'],
                { placeHolder: 'Also delete files?' }
            );
            if (!delPick) return;

            argStr = name;
            if (delPick === 'delete files') argStr += ' --delete';
            break;
        }

        case 'rename': {
            const oldName = await vscode.window.showInputBox({
                prompt: 'Current library name',
                validateInput: v => /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Invalid name',
            });
            if (!oldName) return;
            const newName = await vscode.window.showInputBox({
                prompt: 'New library name',
                validateInput: v => /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Invalid name',
            });
            if (!newName) return;
            argStr = `${oldName} ${newName}`;
            break;
        }

        case 'move': {
            const name = await vscode.window.showInputBox({
                prompt: 'Library name to move',
                validateInput: v => /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Invalid name',
            });
            if (!name) return;
            const dest = await vscode.window.showInputBox({
                prompt: 'Destination (new_name or subdir/new_name)',
                validateInput: v => /^[a-z][a-z0-9_/]*$/.test(v) ? null : 'Use lowercase, underscores, slashes',
            });
            if (!dest) return;
            argStr = `${name} ${dest}`;
            break;
        }

        case 'deps': {
            const name = await vscode.window.showInputBox({
                prompt: 'Library name',
                validateInput: v => /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Invalid name',
            });
            if (!name) return;
            const addRaw = await vscode.window.showInputBox({
                prompt: 'Dependencies to ADD (comma-separated, blank to skip)', value: '',
            });
            const removeRaw = await vscode.window.showInputBox({
                prompt: 'Dependencies to REMOVE (comma-separated, blank to skip)', value: '',
            });
            if (!addRaw && !removeRaw) return;
            argStr = name;
            if (addRaw    && addRaw.trim())    argStr += ` --add ${addRaw.trim()}`;
            if (removeRaw && removeRaw.trim()) argStr += ` --remove ${removeRaw.trim()}`;
            break;
        }

        case 'list':
        case 'tree':
        case 'doctor':
            argStr = '';
            break;

        default:
            return;
    }

    const dryRun = await vscode.window.showQuickPick(['run', 'dry-run'], {
        placeHolder: 'Execute or preview?',
    });
    if (!dryRun) return;
    if (dryRun === 'dry-run') argStr += ' --dry-run';

    runLibtool(root, `${op} ${argStr}`.trim());
}

// ─── activate ─────────────────────────────────────────────────────────────────

function activate(context) {

    // 1. Create new project from template
    const initCmd = vscode.commands.registerCommand(
        'cpp-cmake-scaffolder.init',
        async () => {
            const picked = await vscode.window.showOpenDialog({
                canSelectFiles: false, canSelectFolders: true, openLabel: 'Projeyi Oluştur',
            });
            if (!picked || picked.length === 0) return;
            const targetDir = picked[0].fsPath;

            const projectName = await vscode.window.showInputBox({
                prompt: 'Proje adı (CMake uyumlu: harf/rakam/alt çizgi)',
                value: path.basename(targetDir),
                validateInput: v => /^[A-Za-z_][A-Za-z0-9_]*$/.test(v) ? null : 'Geçersiz isim',
            });
            if (!projectName) return;

            const templateDir = path.join(context.extensionPath, 'templates');
            try {
                copyDir(templateDir, targetDir, projectName);
                vscode.window.showInformationMessage(`✅ "${projectName}" oluşturuldu.`);
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

    // 2. libtool — library management
    const libtoolCmd = vscode.commands.registerCommand(
        'cpp-cmake-scaffolder.libtool',
        libtoolUI
    );

    context.subscriptions.push(initCmd, libtoolCmd);
}

exports.activate = activate;
