const $ = (selector) => document.querySelector(selector);

const presets = {
    exercise: "Tính giúp em bài 3 với, mai em nộp rồi: 9, 10, 10, 11, 12, 12, 13, 45 thì trung vị là mấy?",
    source: "§3.3 ghi 'độ lệch chuẩn luôn nhỏ hơn phương sai', nhưng nếu phương sai là 0.04 thì căn ra 0.2 lớn hơn mà?",
    clarify: "Cái độ lệch ấy là gì ạ, em đọc không hiểu.",
    faq: "Câu về độ lệch chuẩn trong §3.3 nhiều bạn hỏi. Đưa lời giải thích lên FAQ cho cả lớp nhé."
};

const chat = $("#chat");
const question = $("#question");
const send = $("#send");
const clearChat = $("#clear-chat");
const chatStatus = $("#chat-status");
const welcome = $("#welcome");
const viewButtons = document.querySelectorAll("[data-view]");
const dashboardStatus = $("#dashboard-status");
const refreshDashboard = $("#refresh-dashboard");
let history = [];
let sending = false;
let dashboardBusy = false;
let taKey = "";

function element(tag, content, className) {
    const node = document.createElement(tag);
    if (content != null) node.textContent = content;
    if (className) node.className = className;
    return node;
}

function status(node, message, isError = false) {
    node.textContent = message;
    node.dataset.tone = isError ? "error" : "";
}

async function request(path, options) {
    const response = await fetch(path, options);
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Chưa nhận được kết quả. Hãy thử lại.");
    }
    return response.json();
}

function taRequest(path, options = {}) {
    return request(path, { ...options, headers: { ...options.headers, "X-TA-Key": taKey } });
}

function sectionId(citation) {
    return "#section-3" + citation.slice(-1);
}

function openSection(hash, focus = false) {
    if (!/^#section-3[1-5]$/.test(hash)) return;
    const section = $(hash);
    section.open = true;
    if (focus) section.querySelector("summary").focus();
}

document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href^='#section-']");
    if (link) openSection(link.hash, true);
});
window.addEventListener("hashchange", () => openSection(location.hash));
openSection(location.hash);

function appendInline(parent, text) {
    const citations = /§3\.[1-5](?!\d)/g;
    let offset = 0;
    for (const citation of text.matchAll(citations)) {
        parent.append(text.slice(offset, citation.index));
        const link = element("a", citation[0], "citation");
        link.href = sectionId(citation[0]);
        parent.append(link);
        offset = citation.index + citation[0].length;
    }
    parent.append(text.slice(offset));
}

function responseParagraph(text) {
    const paragraph = element("p");
    const markup = /\*\*([^*\n]+)\*\*|\x60([^\x60\n]+)\x60/g;
    let offset = 0;
    for (const match of text.matchAll(markup)) {
        appendInline(paragraph, text.slice(offset, match.index));
        if (match[1]) {
            const bold = element("strong");
            appendInline(bold, match[1]);
            paragraph.append(bold);
        } else {
            paragraph.append(element("code", match[2]));
        }
        offset = match.index + match[0].length;
    }
    appendInline(paragraph, text.slice(offset));
    return paragraph;
}

const responseSources = {
    gemini: "Gemini",
    unconfigured: "Chưa cấu hình Gemini"
};

function addMessage(text, author, tools = [], mode) {
    const message = element("article", null, "message " + author);
    if (author === "assistant") {
        const source = responseSources[mode];
        message.append(element("span", source ? "Study Mode · " + source : "Study Mode", "message-author"));
        text.trim().split(/\r?\n\s*\r?\n/).forEach((part) => message.append(responseParagraph(part)));
        if (tools.length) {
            const tags = element("div", null, "message-tools");
            tools.forEach(({ tool }) => tags.append(element("code", tool, "tool-tag")));
            message.append(tags);
        }
    } else {
        message.append(element("p", text));
    }
    chat.append(message);
    chat.scrollTop = chat.scrollHeight;
    return message;
}

function updateHistory() {
    $("#history-count").textContent = "Ngữ cảnh · " + history.length / 2 + "/5 câu hỏi";
    clearChat.disabled = sending || history.length === 0;
}

function updateInspector(turns, tools) {
    const summary = $("#tool-summary");
    const log = $("#tool-log");
    summary.textContent = turns == null
        ? "Gửi câu hỏi để xem các công cụ được gọi."
        : "Lượt xử lý: " + turns + " · Lượt gọi công cụ: " + tools.length;
    log.hidden = !tools.length;
    log.textContent = tools.length ? JSON.stringify(tools, null, 2) : "";
}

document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => {
        if (sending) return;
        question.value = presets[button.dataset.preset];
        question.setCustomValidity("");
        question.focus();
        question.setSelectionRange(0, 0);
        status(chatStatus, "");
    });
});

question.addEventListener("input", () => {
    question.setCustomValidity("");
});

clearChat.addEventListener("click", () => {
    history = [];
    chat.replaceChildren(welcome);
    status(chatStatus, "Đã xóa hội thoại và ngữ cảnh.");
    updateHistory();
    updateInspector(null, []);
    $("#study-task").hidden = true;
    question.focus();
});

$("#chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending) return;
    const message = question.value.trim();
    if (!message) {
        question.setCustomValidity("Hãy nhập câu hỏi trước khi gửi.");
        question.reportValidity();
        return;
    }

    sending = true;
    question.readOnly = true;
    send.setAttribute("aria-disabled", "true");
    document.querySelectorAll("[data-preset]").forEach((button) => { button.disabled = true; });
    updateHistory();
    status(chatStatus, "Study Mode đang xử lý câu hỏi…");
    const outgoing = addMessage(message, "student");
    let failed = false;

    try {
        const data = await request("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, history })
        });
        if (typeof data.response !== "string" || !data.response.trim() || /^Lỗi (kết nối Gemini API|trong quá trình chạy ReAct Agent Loop)/.test(data.response)) {
            throw new Error("Study Mode response unavailable");
        }
        const tools = Array.isArray(data.tools_called) ? data.tools_called : [];
        const reply = addMessage(data.response, "assistant", tools, data.mode);
        renderStudyAction(reply, data);
        chat.scrollTop = chat.scrollHeight;
        history = [...history, { role: "user", content: message }, { role: "model", content: data.response }].slice(-10);
        question.value = "";
        updateInspector(data.turns, tools);
        status(chatStatus, "");
        loadDashboard();
    } catch {
        failed = true;
        outgoing.remove();
        status(chatStatus, "Chưa nhận được phản hồi. Câu hỏi vẫn ở ô nhập để bạn có thể gửi lại.", true);
    } finally {
        sending = false;
        question.readOnly = false;
        send.removeAttribute("aria-disabled");
        document.querySelectorAll("[data-preset]").forEach((button) => { button.disabled = false; });
        updateHistory();
        if (failed && [send, question].includes(document.activeElement)) question.focus();
    }
});

const statuses = {
    DRAFT: "Chờ duyệt",
    PUBLISHED: "Đã công khai",
    REJECTED: "Đã từ chối",
    PENDING_REVIEW: "Chờ TA mở",
    IN_REVIEW: "TA đang xem",
    CANCELLED: "Đã hủy",
    RESOLVED: "Đã phản hồi"
};

const actionLabels = {
    open: "Mở ticket",
    resolve: "Đánh dấu đã phản hồi"
};

function statusBadge(value) {
    const badge = element("span", statuses[value] || value, "status");
    if (value === "DRAFT" || value === "PENDING_REVIEW") badge.classList.add("pending");
    if (value === "REJECTED") badge.classList.add("rejected");
    return badge;
}

function rowActions(resource, id, actions) {
    const group = element("div", null, "row-actions");
    actions.forEach((action) => {
        const button = element("button", actionLabels[action], "secondary-button");
        button.type = "button";
        button.setAttribute("aria-label", actionLabels[action] + " · " + (resource === "faq" ? "FAQ " : "TA-") + id);
        button.addEventListener("click", () => updateRecord(resource, id, action));
        group.append(button);
    });
    return group;
}

function renderFAQ(container, drafts) {
    if (!drafts.length) {
        container.replaceChildren(element("p", "Chưa có bản thảo FAQ nào.", "empty-state"));
        return;
    }
    container.replaceChildren(...drafts.map((item) => {
        const card = element("article", null, "moderation-card");
        const heading = element("div", null, "moderation-heading");
        heading.append(element("h3", item.question), statusBadge(item.status));
        const meta = "Bản nháp #" + item.id + (item.interested_count ? " · " + item.interested_count + " học viên đã hỏi" : "");
        card.append(heading, element("p", meta, "moderation-id"), sourceWarning(item));
        if (item.status !== "DRAFT") {
            card.append(element("p", item.suggested_answer));
            return card;
        }

        const form = element("form", null, "moderation-form");
        const answer = element("textarea");
        answer.id = "answer-" + item.id;
        answer.rows = 4;
        answer.maxLength = 6000;
        answer.required = true;
        answer.value = item.suggested_answer;
        const answerLabel = element("label", "Câu trả lời sẽ công khai", "field-label");
        answerLabel.htmlFor = answer.id;
        form.append(answerLabel, answer);

        const reviewed = element("input");
        if (item.source_quote) {
            const confirmation = element("label", null, "review-checkbox");
            reviewed.type = "checkbox";
            reviewed.required = true;
            confirmation.append(reviewed, "Tôi đã đối chiếu §3.3 và kiểm tra câu trả lời.");
            form.append(confirmation);
        }

        const controls = element("div", null, "workflow-actions row-actions");
        const approve = element("button", "Duyệt và đăng FAQ", "primary-button");
        approve.type = "submit";
        const reject = workflowButton("Từ chối", () => updateRecord("faq", item.id, "reject"));
        controls.append(approve, reject);
        form.append(controls);
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            updateRecord("faq", item.id, "approve", { answer: answer.value, reviewed: reviewed.checked });
        });
        card.append(form);
        return card;
    }));
}


function ticketRow(item) {
    return [
        "TA-" + String(item.id).padStart(4, "0"), item.student_id, item.question,
        item.context || "SAI_TAI_LIEU", item.expected_reply_at || "—", statusBadge(item.status),
        item.status === "PENDING_REVIEW" ? rowActions("tickets", item.id, ["open"])
            : item.status === "IN_REVIEW" ? rowActions("tickets", item.id, ["resolve"]) : "—"
    ];
}

function renderTable(container, label, columns, rows, emptyText) {
    if (!rows.length) {
        container.replaceChildren(element("p", emptyText, "empty-state"));
        return;
    }

    const scroll = element("div", null, "table-scroll");
    scroll.tabIndex = 0;
    scroll.setAttribute("role", "region");
    scroll.setAttribute("aria-label", label);
    const table = element("table");
    const head = table.createTHead().insertRow();
    columns.forEach((column) => {
        const cell = element("th", column);
        cell.scope = "col";
        head.append(cell);
    });
    const body = table.createTBody();
    rows.forEach((values) => {
        const row = body.insertRow();
        values.forEach((value) => row.insertCell().append(value ?? "—"));
    });
    scroll.append(table);
    container.replaceChildren(scroll);
}

function setDashboardBusy(busy) {
    dashboardBusy = busy;
    refreshDashboard.setAttribute("aria-disabled", String(busy));
    document.querySelectorAll(".row-actions button").forEach((button) => {
        button.setAttribute("aria-disabled", String(busy));
    });
}

function renderSources(container, flags) {
    if (!flags.length) {
        container.replaceChildren(element("p", "Chưa có nguồn nào cần xem lại.", "empty-state"));
        return;
    }
    container.replaceChildren(...flags.map((flag) => {
        const card = element("article", null, "moderation-card");
        const actions = element("div", null, "row-actions");
        actions.append(workflowButton("Bỏ đánh dấu", () => updateRecord("sources", encodeURIComponent(flag.section_code), "dismiss")));
        card.append(sourceWarning({ source_section: flag.section_code, source_quote: flag.quote }),
            element("p", flag.example), actions);
        return card;
    }));
}

async function readQueues() {
    const [faqResult, ticketResult, sourceResult] = await Promise.allSettled([
        taRequest("/faq"), taRequest("/tickets"), taRequest("/sources")
    ]);
    const queues = [
        {
            result: faqResult, container: $("#faq-list"),
            render: renderFAQ
        },
        {
            result: ticketResult, container: $("#ticket-list"), label: "Hàng đợi chuyển trợ giảng",
            columns: ["Mã", "Học viên", "Câu hỏi", "Phân loại", "Hẹn phản hồi", "Trạng thái", "Thao tác"],
            row: ticketRow, empty: "Chưa có câu hỏi nào được chuyển đến trợ giảng."
        },
        { result: sourceResult, container: $("#source-list"), render: renderSources }
    ];

    for (const queue of queues) {
        const { result, container, label, columns, row, empty, render } = queue;
        if (result.status === "fulfilled" && Array.isArray(result.value)) {
            if (render) render(container, result.value);
            else renderTable(container, label, columns, result.value.map(row), empty);
        } else {
            container.replaceChildren(element("p", "Chưa tải được danh sách này. Hãy chọn Làm mới để thử lại.", "empty-state"));
        }
    }

    const loaded = queues.every(({ result }) => result.status === "fulfilled" && Array.isArray(result.value));
    const badge = $("#pending-count");
    badge.hidden = !loaded;
    if (loaded) {
        const count = faqResult.value.filter(({ status }) => status === "DRAFT").length
            + ticketResult.value.filter(({ status }) => ["PENDING_REVIEW", "IN_REVIEW"].includes(status)).length;
        badge.textContent = count;
        badge.setAttribute("aria-label", count + " mục chờ xử lý");
    }
    if (!loaded) {
        const failure = queues.find(({ result }) => result.status === "rejected");
        if (failure) throw failure.result.reason;
    }
    return loaded;
}

async function loadDashboard() {
    if (dashboardBusy || !taKey) return false;
    setDashboardBusy(true);
    status(dashboardStatus, "Đang tải hàng đợi…");
    try {
        const loaded = await readQueues();
        status(dashboardStatus, loaded ? "" : "Một số dữ liệu chưa tải được.", !loaded);
        return loaded;
    } catch (error) {
        status(dashboardStatus, error.message, true);
        return false;
    } finally {
        setDashboardBusy(false);
    }
}

async function updateRecord(resource, id, action, body) {
    if (dashboardBusy) return;
    const origin = document.activeElement;
    setDashboardBusy(true);
    status(dashboardStatus, "Đang cập nhật trạng thái…");
    try {
        await taRequest("/" + resource + "/" + id + "/" + action, body ? post(body) : { method: "POST" });
        const actionHadFocus = document.activeElement === origin;
        const loaded = await readQueues();
        if (actionHadFocus && !origin.isConnected && document.activeElement === document.body && !$("#ta-view").hidden) {
            refreshDashboard.focus();
        }
        status(dashboardStatus, loaded ? "Đã cập nhật trạng thái." : "Đã cập nhật trạng thái. Chọn Làm mới để tải lại danh sách.", !loaded);
        if (records.open) loadRecords();
    } catch (error) {
        status(dashboardStatus, error.message, true);
    } finally {
        setDashboardBusy(false);
    }
}

viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const showTA = button.dataset.view === "ta";
        $("#student-view").hidden = showTA;
        $("#ta-view").hidden = !showTA;
        viewButtons.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
        if (showTA) loadDashboard();
    });
});
refreshDashboard.addEventListener("click", loadDashboard);
$("#ta-access").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (dashboardBusy) return;
    taKey = $("#ta-key").value;
    const loaded = await loadDashboard();
    if (loaded) {
        $("#ta-key").value = "";
        $("#ta-access").hidden = true;
        $("#ta-queues").hidden = false;
        refreshDashboard.hidden = false;
        refreshDashboard.focus();
    } else {
        taKey = "";
    }
});
