const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

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

function isBinary(filePath) { return BINARY_EXTS.has(path.extname(filePath).toLowerCase()); }
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

// ─── toollib runner ───────────────────────────────────────────────────────────

function getWorkspaceRoot() {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? null;
}

function runToollib(workspaceRoot, args) {
    const script = path.join(workspaceRoot, 'scripts', 'toollib.py');
    if (!fs.existsSync(script)) {
        vscode.window.showErrorMessage(
            'toollib.py not found. Is this a CppCmakeProjectTemplate project?'
        );
        return;
    }
    const terminal = vscode.window.createTerminal({
        name: 'toollib',
        cwd: workspaceRoot,
    });
    terminal.show();
    terminal.sendText(`python3 "${script}" ${args}`);
}

// ─── toollib UI ───────────────────────────────────────────────────────────────

async function toollibUI() {
    const root = getWorkspaceRoot();
    if (!root) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }

    const OP_ITEMS = [
        { label: '$(add)    add', description: 'Create a new library skeleton', op: 'add' },
        { label: '$(trash)  remove', description: 'Detach or delete a library', op: 'remove' },
        { label: '$(edit)   rename', description: 'Rename a library (all references)', op: 'rename' },
        { label: '$(arrow-right) move', description: 'Move library to new location/subdir', op: 'move' },
        { label: '$(link)   deps', description: 'Add or remove library dependencies', op: 'deps' },
        { label: '$(list-unordered) list', description: 'List all libraries', op: 'list' },
        { label: '$(type-hierarchy) tree', description: 'Show ASCII dependency tree', op: 'tree' },
        { label: '$(check)  doctor', description: 'Check project consistency', op: 'doctor' },
    ];

    const picked = await vscode.window.showQuickPick(OP_ITEMS, {
        placeHolder: 'toollib: select operation',
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
            if (depsRaw && depsRaw.trim()) argStr += ` --deps ${depsRaw.trim()}`;
            if (linkPick === 'yes') argStr += ' --link-app';
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
            if (addRaw && addRaw.trim()) argStr += ` --add ${addRaw.trim()}`;
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

    runToollib(root, `${op} ${argStr}`.trim());
}

// ─── toolsolution UI ───────────────────────────────────────────────────────────

async function toolsolutionUI() {
    const root = getWorkspaceRoot();
    if (!root) { vscode.window.showErrorMessage('No workspace folder open.'); return; }

    const OP_ITEMS = [
        { label: '$(list-unordered) target list', description: 'List all libs and apps', op: 'target list' },
        { label: '$(play)          target build', description: 'Build a single target', op: 'target build' },
        { label: '$(add)           preset add', description: 'Add a new CMake preset', op: 'preset add' },
        { label: '$(trash)         preset remove', description: 'Remove a preset', op: 'preset remove' },
        { label: '$(list-ordered)  preset list', description: 'List all presets', op: 'preset list' },
        { label: '$(tools)         toolchain add', description: 'Add toolchain from template', op: 'toolchain add' },
        { label: '$(list-ordered)  toolchain list', description: 'List toolchains', op: 'toolchain list' },
        { label: '$(gear)          config get', description: 'Show project config', op: 'config get' },
        { label: '$(gear)          config set', description: 'Set a base preset variable', op: 'config set' },
        { label: '$(check)         doctor', description: 'Full project health check', op: 'doctor' },
    ];

    const picked = await vscode.window.showQuickPick(OP_ITEMS, {
        placeHolder: 'toolsolution: select operation', matchOnDescription: true,
    });
    if (!picked) return;

    const script = path.join(root, 'scripts', 'toolsolution.py');
    if (!fs.existsSync(script)) {
        vscode.window.showErrorMessage('toolsolution.py not found.');
        return;
    }

    let argStr = picked.op;

    if (picked.op === 'target build') {
        const name = await vscode.window.showInputBox({ prompt: 'Target name (e.g. main_app, dummy_lib)' });
        if (!name) return;
        argStr = `target build ${name}`;
    } else if (picked.op === 'preset add') {
        const compiler = await vscode.window.showQuickPick(['gcc', 'clang', 'msvc'], { placeHolder: 'Compiler' });
        const type = await vscode.window.showQuickPick(['debug', 'release', 'relwithdebinfo'], { placeHolder: 'Type' });
        const link = await vscode.window.showQuickPick(['static', 'dynamic'], { placeHolder: 'Linking' });
        const arch = await vscode.window.showQuickPick(['x86_64', 'x86'], { placeHolder: 'Arch' });
        if (!compiler || !type || !link || !arch) return;
        argStr = `preset add --compiler ${compiler} --type ${type} --link ${link} --arch ${arch}`;
    } else if (picked.op === 'preset remove') {
        const name = await vscode.window.showInputBox({ prompt: 'Preset name to remove' });
        if (!name) return;
        argStr = `preset remove ${name}`;
    } else if (picked.op === 'toolchain add') {
        const name = await vscode.window.showInputBox({ prompt: 'Toolchain name (no extension)' });
        const template = await vscode.window.showQuickPick(['custom-gnu', 'arm-none-eabi'], { placeHolder: 'Template' });
        const prefix = await vscode.window.showInputBox({ prompt: 'Compiler prefix (e.g. /opt/sdk/bin/arm-eabi-)', value: '' });
        const cpu = await vscode.window.showInputBox({ prompt: 'CPU (e.g. cortex-m4)', value: '' });
        const fpu = await vscode.window.showInputBox({ prompt: 'FPU (e.g. fpv4-sp-d16, blank to skip)', value: '' });
        const genPreset = await vscode.window.showQuickPick(['yes', 'no'], { placeHolder: 'Generate preset?' });
        if (!name || !template) return;
        argStr = `toolchain add --name ${name} --template ${template}`;
        if (prefix) argStr += ` --prefix ${prefix}`;
        if (cpu) argStr += ` --cpu ${cpu}`;
        if (fpu) argStr += ` --fpu ${fpu}`;
        if (genPreset === 'yes') argStr += ' --gen-preset';
    } else if (picked.op === 'config set') {
        const key = await vscode.window.showInputBox({ prompt: 'Cache variable name (e.g. ENABLE_ASAN)' });
        const val = await vscode.window.showInputBox({ prompt: 'Value (e.g. ON)' });
        if (!key || !val) return;
        argStr = `config set ${key} ${val}`;
    }

    const terminal = vscode.window.createTerminal({ name: 'toolsolution', cwd: root });
    terminal.show();
    terminal.sendText(`python3 "${script}" ${argStr}`);
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

    // 2. toollib — library management
    const toollibCmd = vscode.commands.registerCommand(
        'cpp-cmake-scaffolder.toollib',
        toollibUI
    );

    // 3. toolsolution — project orchestrator
    const toolsolutionCmd = vscode.commands.registerCommand(
        'cpp-cmake-scaffolder.toolsolution',
        toolsolutionUI
    );

    context.subscriptions.push(initCmd, toollibCmd, toolsolutionCmd);
}

exports.activate = activate;
