// const x = Array.from({ length: 201 }, (_, i) => -10 + i * 0.1);

// const traces = [
//   { x, y: x.map(v => Math.sin(5 * v)), name: "sin(5x)", mode: "lines" },
//   { x, y: x.map(v => Math.cos(v)), name: "cos(x)", mode: "lines" },
//   // { x, y: x.map(v => v ** 2 / 10), name: "x²/10", mode: "lines" },
// ];

// Plotly.newPlot("graph", traces, {
//   title: "Compare functions",
//   xaxis: { title: "x" },
//   yaxis: { title: "y" },
// });

let serverVersion = null;
let checkingServerVersion = false;
const API_BASE = window.location.port === "5500" ? "http://127.0.0.1:8000" : "";

function renderMath(elementId, expression) {
    katex.render(expression, document.getElementById(elementId), {
        displayMode: true,
        throwOnError: false,
    });
}

async function generateResult() {
    const button = document.getElementById("randomIntegral");
    const errorMessage = document.getElementById("error");
    button.disabled = true;
    errorMessage.textContent = "";

    try {
        const response = await fetch(`${API_BASE}/api/integral`, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }



        const result = await response.json();
        serverVersion = result.server_version;
        renderMath("integral", result.expression_latex);
        renderMath("derivative", result.derivative_latex);
        renderMath("integralResult", `\\int ${result.derivative_latex} dx`);
        if (result.risch_latex) {
            renderMath("risch", result.risch_latex);
        } else {
            document.getElementById("risch").textContent =
                result.risch_error || "Risch result is unavailable.";
        }
        if (result.symIntegral_latex) {
            renderMath("symIntegral", result.symIntegral_latex);
        } else {
            document.getElementById("symIntegral").textContent =
                result.symIntegral_error || "SymPy integral is unavailable.";
        }

        if (
            !Array.isArray(result.x_values) ||
            !Array.isArray(result.expression_values) ||
            result.x_values.length !== result.expression_values.length
        ) {
            throw new Error(
                "The Python server is out of date. Restart it with .venv-py39/bin/python ui/server.py --reload."
            );
        }

        const traces = [
            { x: result.x_values, y: result.expression_values, name: "Expression", mode: "lines" },
        ];
        if (result.risch_values) {
            traces.push({
                x: result.x_values,
                y: result.risch_values,
                name: "Risch",
                mode: "lines",
            });
        }
        if (result.symIntegral_values) {
            traces.push({
                x: result.x_values,
                y: result.symIntegral_values,
                name: "SymPy integral of derivative",
                mode: "lines",
            });
        }

        Plotly.newPlot("graph", traces, {
            title: "Compare functions",
            xaxis: { title: "x" },
            yaxis: { title: "y" },
        });

    } catch (error) {
        errorMessage.textContent = error instanceof Error ? error.message : String(error);
    } finally {
        button.disabled = false;
    }
}

async function checkServerVersion() {
    if (checkingServerVersion) {
        return;
    }
    checkingServerVersion = true;

    try {
        const response = await fetch(`${API_BASE}/api/version`, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        const { version } = await response.json();
        if (!serverVersion || version !== serverVersion) {
            serverVersion = version;
            await generateResult();
        } else {
            serverVersion = version;
        }
    } catch {
        document.getElementById("error").textContent =
            "Cannot reach the Python server. Start it with .venv-py39/bin/python ui/server.py --reload.";
    } finally {
        checkingServerVersion = false;
    }
}

document.getElementById("randomIntegral").addEventListener("click", generateResult);
generateResult();
window.setInterval(checkServerVersion, 1000);
