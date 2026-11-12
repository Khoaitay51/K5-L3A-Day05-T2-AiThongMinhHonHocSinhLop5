const task = $("#study-task");
const ticketPanel = $("#ticket-panel");
const ticketQuestion = $("#ticket-question");
const ticketStatus = $("#ticket-status");
const records = $("#student-records");
let ticketOrigin;
let requestId;
let ticketIsAssignment;
let ticketSending = false;
let recordsBusy = false;
let lastRecords;
const pendingDrafts = new Set();

function reveal(panel, heading) {
    panel.hidden = false;
    heading.tabIndex = -1;
    heading.focus();
    panel.scrollIntoView({ block: "nearest" });
}

function showTask(title, ...content) {
    delete task.dataset.draft;
    const heading = element("h2", title);
    task.replaceChildren(heading, ...content);
    reveal(task, heading);
}

function workflowButton(label, handler, primary = false) {
    const button = element("button", label, primary ? "primary-button" : "secondary-button");
    button.type = "button";
    button.addEventListener("click", handler);
    return button;
}

function workflowLink(message, label, handler) {
    const button = workflowButton(label, handler);
    button.classList.add("message-action");
    message.append(button);
}

function post(body) {
    return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function updateAssignmentLabel(data) {
    $("#assignment-label").textContent = data.open ? "Bài tập 3 đang mở" : "Bài tập 3 đã hết hạn";
    $("#assignment-deadline").textContent = data.open && data.minutes_left <= 60
        ? "Còn " + data.minutes_left + " phút · Hạn 23:59 ngày 13/11"
        : "Hạn nộp 23:59 ngày 13/11";
}

function stepCard(title, text, locked = false) {
    const node = element("section", null, "step-card" + (locked ? " locked" : ""));
    node.append(element("h3", title), responseParagraph(text));
    return node;
}

function attemptForm() {
    const form = element("form", null, "attempt-form");
    const inputs = element("div", null, "attempt-fields");
    const fields = ["Giá trị thứ nhất", "Giá trị thứ hai"].map((name, index) => {
        const label = element("label", name, "field-label");
        const input = element("input");
        input.required = true;
        input.inputMode = "decimal";
        input.maxLength = 24;
        input.id = "attempt-value-" + index;
        label.htmlFor = input.id;
        label.append(input);
        inputs.append(label);
        return input;
    });
    const button = element("button", "Gửi kết quả bước 1", "primary-button");
    const feedback = element("p", null, "workflow-status");
    feedback.setAttribute("role", "status");
    form.append(inputs, button, feedback);
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (button.disabled) return;
        button.disabled = true;
        status(feedback, "Đang lưu bước 1…");
        try {
            const data = await request("/study/assignment/attempt", post({ first: fields[0].value, second: fields[1].value }));
            showAssignment(data, true);
        } catch (error) {
            status(feedback, error.message, true);
            button.disabled = false;
        }
    });
    return form;
}

function showAssignment(data, advance = false) {
    updateAssignmentLabel(data);
    const deadline = element("p", $("#assignment-deadline").textContent, "assignment-timing");
    if (!data.open) {
        showTask("Hướng dẫn Bài tập 3", deadline, stepCard("Lời giải · Đã mở", data.solution));
        return;
    }
    const first = stepCard(data.step === 1 ? "Bước 1 · Đang mở" : "Bước 1 · Đã gửi kết quả", data.hint_one);
    if (data.step === 1) first.append(attemptForm());
    const second = stepCard(
        data.step === 1 ? "Bước 2 · Đang khóa" : "Bước 2 · Đang mở",
        data.hint_two || "Gửi hai giá trị em tìm được ở bước 1 để mở gợi ý tiếp theo.",
        data.step === 1
    );
    const solution = stepCard("Lời giải · Đang khóa", "Mở sau hạn nộp lúc 23:59 ngày 13/11.", true);
    const ta = element("div", null, "step-card locked");
    const sendToTa = workflowButton("Vẫn gửi cho TA", () => showTicket(
        "Em cần trợ giúp về Bài tập 3. Em đã xem gợi ý đến bước " + data.step + ".",
        data.ta_reply, sendToTa, true
    ));
    const timing = data.ta_after_deadline ? " Ca trực tiếp theo bắt đầu sau hạn nộp." : "";
    ta.append(element("h3", "Hỏi trợ giảng"), element("p", data.ta_reply + timing), sendToTa);
    showTask("Hướng dẫn Bài tập 3", deadline, first, second, solution, ta);
    if (advance) reveal(task, second.querySelector("h3"));
}

async function openAssignment() {
    try {
        showAssignment(await request("/study/assignment"));
    } catch {
        showTask("Hướng dẫn Bài tập 3", element("p", "Chưa tải được trạng thái bài tập. Hãy mở lại để thử."));
    }
}

function sourceWarning(draft) {
    if (!draft.source_quote) return element("span");
    const warning = element("div", null, "notice source-warning");
    warning.append(
        element("strong", draft.source_section + " · Cần TA xem lại"),
        element("p", "“" + draft.source_quote + "”")
    );
    return warning;
}

function showDraft(draft) {
    const actions = element("div", null, "workflow-actions");
    const cancel = workflowButton("Hủy đề xuất", () => cancelRecord("faq", draft.id, cancel));
    const report = workflowButton("Báo chỗ sai khác", () => showTicket("", null, report));
    if (draft.status === "DRAFT") actions.append(cancel);
    actions.append(report);
    showTask("Bản nháp FAQ · " + statuses[draft.status].toLocaleLowerCase("vi"),
        element("p", draft.question, "workflow-question"), sourceWarning(draft),
        element("p", draft.suggested_answer), actions
    );
    task.dataset.draft = draft.id;
}

function newRequestId() {
    return crypto.randomUUID();
}

async function showTicket(text, eta, origin, isAssignment = false) {
    if (ticketSending) return;
    ticketOrigin = origin;
    requestId = newRequestId();
    const openingId = requestId;
    ticketIsAssignment = isAssignment;
    ticketQuestion.value = text;
    $("#ticket-form").hidden = false;
    $("#ticket-eta").textContent = eta || "Giờ trực TA 08:00–22:00. Phản hồi theo hàng đợi.";
    status(ticketStatus, "");
    reveal(ticketPanel, $("#ticket-title"));
    if (!eta) {
        try {
            const data = await request("/study/records");
            if (requestId === openingId) $("#ticket-eta").textContent = data.ta_reply;
        } catch { /* office hours remain available */ }
    }
}

$("#close-ticket").addEventListener("click", () => {
    ticketPanel.hidden = true;
    if (ticketOrigin?.isConnected) ticketOrigin.focus();
});
$("#ticket-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const sendButton = event.currentTarget.querySelector("[type='submit']");
    if (ticketSending) return;
    ticketSending = true;
    sendButton.disabled = true;
    $("#close-ticket").disabled = true;
    ticketQuestion.readOnly = true;
    status(ticketStatus, "Đang gửi yêu cầu…");
    try {
        const result = await request("/study/tickets", post({ question: ticketQuestion.value, request_id: requestId, assignment: ticketIsAssignment }));
        status(ticketStatus, "Đã chuyển yêu cầu TA-" + String(result.id).padStart(4, "0") + ". " + result.expected_reply_at);
        $("#ticket-form").hidden = true;
        records.open = true;
        await loadRecords();
        loadDashboard();
    } catch (error) {
        status(ticketStatus, error.message, true);
    } finally {
        ticketSending = false;
        sendButton.disabled = false;
        $("#close-ticket").disabled = false;
        ticketQuestion.readOnly = false;
    }
});

function renderStudyAction(message, data) {
    if (data.assignment) {
        updateAssignmentLabel(data.assignment);
        workflowLink(message, "Mở hướng dẫn Bài tập 3", openAssignment);
    }
    if (data.faq_draft) {
        pendingDrafts.add(data.faq_draft.id);
        workflowLink(message, "Xem bản nháp FAQ", async () => {
            try {
                const { drafts } = await request("/study/records");
                const current = drafts.find(({ id }) => id === data.faq_draft.id);
                if (current) showDraft(current);
                else showTask("Bản nháp FAQ", element("p", "Bản nháp này đã nằm ngoài danh sách gần đây."));
            } catch (error) {
                showTask("Bản nháp FAQ", element("p", error.message));
            }
        });
        if (records.open) loadRecords();
    }
    if (data.ta_offer) {
        const button = workflowButton("Xem trước yêu cầu gửi TA", () => showTicket(
            data.ta_offer.question, data.ta_offer.expected_reply_at, button
        ));
        button.classList.add("message-action");
        message.append(button);
    }
}

async function cancelRecord(kind, id, button) {
    if (button.disabled) return;
    button.disabled = true;
    records.open = true;
    const feedback = $("#records-status");
    try {
        await request("/study/" + (kind === "faq" ? "faq" : "tickets") + "/" + id + "/cancel", { method: "POST" });
        if (kind === "faq" && task.dataset.draft === String(id)) {
            showTask("Đã hủy đề xuất FAQ", element("p", "Bản nháp đã rời hàng chờ duyệt."));
        }
        await loadRecords();
        status(feedback, kind === "faq" ? "Đã hủy đề xuất FAQ." : "Đã hủy yêu cầu gửi TA.");
        loadDashboard();
    } catch (error) {
        await loadRecords();
        status(feedback, error.message, true);
    } finally {
        button.disabled = false;
    }
}

function renderRecords(data) {
    const groups = [
        ["Đề xuất FAQ của bạn", data.drafts, (draft) => {
            const button = workflowButton(statuses[draft.status], () => showDraft(draft));
            return [element("strong", draft.question), button];
        }],
        ["Yêu cầu đã chuyển TA", data.tickets, (ticket) => {
            const items = [
                element("strong", "TA-" + String(ticket.id).padStart(4, "0") + " · " + statuses[ticket.status]),
                element("p", ticket.question)
            ];
            if (ticket.status === "PENDING_REVIEW") {
                const cancel = workflowButton("Hủy yêu cầu", () => cancelRecord("ticket", ticket.id, cancel));
                items.push(cancel);
            }
            return items;
        }],
        ["FAQ đã công khai", data.published, (item) => [
            element("strong", item.question), element("p", item.suggested_answer)
        ]]
    ];
    $("#record-list").replaceChildren(...groups.map(([title, items, render]) => {
        const group = element("section", null, "record-group");
        group.append(element("h3", title));
        if (!items.length) group.append(element("p", "Chưa có mục nào."));
        items.forEach((item) => {
            const row = element("div", null, "record-row");
            row.append(...render(item));
            group.append(row);
        });
        return group;
    }));
}

async function loadRecords() {
    if (recordsBusy) return;
    recordsBusy = true;
    const feedback = $("#records-status");
    const previous = document.activeElement;
    try {
        const data = await request("/study/records");
        const snapshot = JSON.stringify(data);
        const firstLoad = !lastRecords;
        if (snapshot !== lastRecords) {
            renderRecords(data);
            lastRecords = snapshot;
        }
        const published = data.drafts.find(({ id, status }) => (firstLoad || pendingDrafts.has(id)) && status === "PUBLISHED");
        data.drafts.forEach(({ id, status }) => {
            if (status === "DRAFT") pendingDrafts.add(id);
            else pendingDrafts.delete(id);
        });
        if (published) {
            const notice = $("#publication-notice");
            notice.textContent = "FAQ đã công khai: " + published.question;
            notice.hidden = false;
        }
        status(feedback, "");
        if (!previous.isConnected && document.activeElement === document.body && records.open) {
            records.querySelector("summary").focus();
        }
    } catch (error) {
        status(feedback, error.message, true);
    } finally {
        recordsBusy = false;
    }
}

records.addEventListener("toggle", () => { if (records.open) loadRecords(); });
window.addEventListener("focus", () => { if (records.open || pendingDrafts.size) loadRecords(); });
window.setInterval(() => {
    if (!document.hidden && (records.open || pendingDrafts.size)) loadRecords();
}, 15000);
$("#open-assignment").addEventListener("click", openAssignment);
request("/study/assignment").then(updateAssignmentLabel).catch(() => {});
loadRecords();
