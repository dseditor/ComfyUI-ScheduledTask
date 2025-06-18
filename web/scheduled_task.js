import { app } from "../../scripts/app.js";

let globalEnabled = false;
let schedules = [];
let workflows = [];
let settingsContainer = null;

// Save workflow as task
async function saveWorkflowAsTask() {
    try {
        // Check if there are nodes in the current graph
        if (!app.graph || !app.graph._nodes || app.graph._nodes.length === 0) {
            showNotification("No workflow to save!", "error");
            return;
        }

        // Show naming dialog
        const workflowName = await showNamingDialog();
        if (!workflowName) {
            return; // User cancelled
        }

        // Get pure API format (without _meta and other workflow metadata)
        let apiWorkflow;
        try {
            // Use ComfyUI's graphToPrompt to get the API format
            const promptData = await app.graphToPrompt();
            
            // promptData.output contains the API format we need
            if (promptData.output) {
                apiWorkflow = promptData.output;
            } else if (promptData.workflow) {
                // If output is not available, clean the workflow format
                apiWorkflow = cleanWorkflowToAPI(promptData.workflow);
            } else {
                throw new Error("No valid prompt data generated");
            }
        } catch (error) {
            console.log("graphToPrompt failed, trying manual conversion:", error);
            
            try {
                // Manual conversion as fallback
                const workflow = app.graph.serialize();
                apiWorkflow = convertToAPIFormat(workflow);
            } catch (conversionError) {
                console.error("Manual conversion failed:", conversionError);
                throw new Error("Failed to convert workflow to API format");
            }
        }
        
        if (!apiWorkflow || Object.keys(apiWorkflow).length === 0) {
            throw new Error("Generated API workflow is empty");
        }

        console.log("Generated API workflow:", apiWorkflow);
        
        // Save workflow
        const response = await fetch('/scheduledtask/save_workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: workflowName,
                workflow: apiWorkflow
            })
        });

        if (response.ok) {
            showNotification(`Workflow saved as "${workflowName}.json"`, "success");
            // Refresh workflow list if settings is open
            if (settingsContainer) {
                workflows = await getWorkflowList();
                // Re-render the settings if they're currently displayed
                const newContent = await createScheduleSettings();
                settingsContainer.innerHTML = '';
                settingsContainer.appendChild(newContent);
            }
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
    } catch (error) {
        console.error("Failed to save workflow:", error);
        showNotification("Failed to save workflow: " + error.message, "error");
    }
}

// Clean workflow format to pure API format
function cleanWorkflowToAPI(workflow) {
    const apiWorkflow = {};
    
    Object.keys(workflow).forEach(nodeId => {
        const node = workflow[nodeId];
        
        // Create clean API node (remove _meta and other metadata)
        apiWorkflow[nodeId] = {
            class_type: node.class_type,
            inputs: { ...node.inputs } // Copy inputs without metadata
        };
    });
    
    return apiWorkflow;
}

// Show naming dialog
function showNamingDialog() {
    return new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 10000;
            display: flex;
            justify-content: center;
            align-items: center;
        `;

        // Create dialog
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: white;
            border-radius: 8px;
            padding: 25px;
            min-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;

        // Title
        const title = document.createElement('h3');
        title.textContent = '💾 Save Workflow as Task';
        title.style.cssText = 'margin: 0 0 20px 0; color: #333; text-align: center;';

        // Input container
        const inputContainer = document.createElement('div');
        inputContainer.style.cssText = 'margin-bottom: 20px;';

        const label = document.createElement('label');
        label.textContent = 'Workflow Name:';
        label.style.cssText = 'display: block; margin-bottom: 8px; font-weight: bold; color: #333;';

        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Enter workflow name (without .json extension)';
        input.style.cssText = `
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        `;

        // Auto-generate name based on current time
        const now = new Date();
        const defaultName = `workflow_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}_${now.getHours().toString().padStart(2,'0')}${now.getMinutes().toString().padStart(2,'0')}`;
        input.value = defaultName;
        input.select();

        inputContainer.appendChild(label);
        inputContainer.appendChild(input);

        // Button container
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = 'display: flex; gap: 10px; justify-content: flex-end;';

        // Save button
        const saveButton = document.createElement('button');
        saveButton.textContent = '💾 Save';
        saveButton.style.cssText = `
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        `;

        // Cancel button
        const cancelButton = document.createElement('button');
        cancelButton.textContent = '❌ Cancel';
        cancelButton.style.cssText = `
            padding: 10px 20px;
            background: #f44336;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        `;

        // Event handlers
        function handleSave() {
            const name = input.value.trim();
            if (!name) {
                input.style.borderColor = '#f44336';
                input.focus();
                return;
            }
            
            // Validate filename
            const invalidChars = /[<>:"/\\|?*]/g;
            if (invalidChars.test(name)) {
                showNotification("Invalid characters in filename!", "error");
                input.style.borderColor = '#f44336';
                input.focus();
                return;
            }

            document.body.removeChild(overlay);
            resolve(name);
        }

        function handleCancel() {
            document.body.removeChild(overlay);
            resolve(null);
        }

        saveButton.onclick = handleSave;
        cancelButton.onclick = handleCancel;

        // Enter key to save
        input.onkeydown = (e) => {
            if (e.key === 'Enter') {
                handleSave();
            } else if (e.key === 'Escape') {
                handleCancel();
            }
        };

        // Click overlay to cancel
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                handleCancel();
            }
        };

        buttonContainer.appendChild(saveButton);
        buttonContainer.appendChild(cancelButton);

        dialog.appendChild(title);
        dialog.appendChild(inputContainer);
        dialog.appendChild(buttonContainer);

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        // Focus input
        setTimeout(() => input.focus(), 100);
    });
}

// Convert workflow to API format
function convertToAPIFormat(workflow) {
    try {
        const apiWorkflow = {};
        
        // Convert nodes to API format
        if (workflow.nodes) {
            workflow.nodes.forEach(node => {
                if (node.id !== undefined) {
                    apiWorkflow[node.id.toString()] = {
                        class_type: node.type,
                        inputs: {}
                    };
                    
                    // Process node properties to get input values
                    const nodeInputs = apiWorkflow[node.id.toString()].inputs;
                    
                    // Handle widgets (standalone values)
                    if (node.widgets_values && node.widgets_values.length > 0) {
                        // Get widget names from node definition
                        const nodeClass = LiteGraph.registered_node_types[node.type];
                        if (nodeClass && nodeClass.prototype) {
                            const tempNode = new nodeClass();
                            if (tempNode.widgets) {
                                tempNode.widgets.forEach((widget, index) => {
                                    if (index < node.widgets_values.length) {
                                        nodeInputs[widget.name] = node.widgets_values[index];
                                    }
                                });
                            }
                        }
                    }
                    
                    // Handle connections (linked inputs)
                    if (node.inputs && workflow.links) {
                        node.inputs.forEach((input, inputIndex) => {
                            if (input.link !== null && input.link !== undefined) {
                                // Find the link
                                const link = workflow.links.find(l => l && l[0] === input.link);
                                if (link) {
                                    const sourceNodeId = link[1];
                                    const sourceOutputIndex = link[2];
                                    
                                    nodeInputs[input.name] = [
                                        sourceNodeId.toString(),
                                        sourceOutputIndex
                                    ];
                                }
                            }
                        });
                    }
                    
                    // Fallback: try to get default values from properties
                    if (node.properties) {
                        Object.keys(node.properties).forEach(key => {
                            if (!(key in nodeInputs)) {
                                nodeInputs[key] = node.properties[key];
                            }
                        });
                    }
                }
            });
        }
        
        return apiWorkflow;
    } catch (error) {
        console.error("Error converting workflow to API format:", error);
        
        // If conversion fails, try a simpler approach
        try {
            console.log("Trying alternative conversion method...");
            
            // Use app.graphToPrompt if available
            if (app && app.graphToPrompt) {
                const prompt = app.graphToPrompt();
                if (prompt && prompt.workflow) {
                    return prompt.workflow;
                }
            }
            
            // Last resort: return the original workflow if it's already in API format
            if (workflow && typeof workflow === 'object' && !workflow.nodes) {
                console.log("Using original workflow (appears to be API format)");
                return workflow;
            }
            
            throw new Error("All conversion methods failed");
        } catch (fallbackError) {
            console.error("Fallback conversion also failed:", fallbackError);
            throw new Error("Failed to convert workflow format");
        }
    }
}

// Get workflow list
async function getWorkflowList() {
    try {
        const response = await fetch('/scheduledtask/get_workflows');
        if (response.ok) {
            const data = await response.json();
            return data.workflows || [];
        }
    } catch (error) {
        console.error("Failed to get workflow list:", error);
    }
    return [];
}

// Save schedule settings
async function saveSchedules() {
    try {
        // If globally disabled, clear all schedules
        const finalSchedules = globalEnabled ? schedules.filter(s => 
            s.time && s.workflow && s.enabled
        ) : [];
        
        const response = await fetch('/scheduledtask/save_schedules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                schedules: finalSchedules,
                globalEnabled: globalEnabled 
            })
        });
        
        if (response.ok) {
            console.log("Schedule settings saved and applied");
            showNotification("Schedule settings saved and applied!", "success");
            return true;
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error("Save failed:", error);
        showNotification("Save failed: " + error.message, "error");
    }
    return false;
}

// Load existing schedule settings
async function loadSchedules() {
    try {
        const response = await fetch('/scheduledtask/get_schedules');
        if (response.ok) {
            const data = await response.json();
            globalEnabled = data.globalEnabled || false;
            return data.schedules || [];
        }
    } catch (error) {
        console.error("Failed to load schedule settings:", error);
    }
    return [];
}

// Show notification
function showNotification(message, type = "info") {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-weight: bold;
        z-index: 10000;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 3000);
}

// Create schedule settings interface
async function createScheduleSettings() {
    // Load data
    try {
        const [loadedSchedules, loadedWorkflows] = await Promise.all([
            loadSchedules(),
            getWorkflowList()
        ]);
        
        schedules = loadedSchedules;
        workflows = loadedWorkflows;
        
        // Ensure at least 3 schedule slots
        while (schedules.length < 3) {
            schedules.push({
                time: '',
                workflow: '',
                enabled: false
            });
        }
        
    } catch (error) {
        console.error('Failed to load schedule data:', error);
        schedules = [{time: '', workflow: '', enabled: false}, {time: '', workflow: '', enabled: false}, {time: '', workflow: '', enabled: false}];
        workflows = [];
    }
    
    // Create container
    const container = document.createElement('div');
    container.style.cssText = `
        padding: 15px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        background: #fafafa;
        margin: 8px 0;
        max-width: 100%;
    `;
    
    // Description
    const description = document.createElement('div');
    description.innerHTML = `
        <div style="margin-bottom: 15px; padding: 10px; background: #e8f4fd; border-left: 4px solid #2196F3; border-radius: 4px; font-size: 12px;">
            <strong>💡 Info:</strong> Workflow API files should be placed in <strong>ComfyUI-ScheduledTask/Workflow/</strong> folder.
        </div>
    `;
    
    // Global switch container
    const globalSwitchContainer = document.createElement('div');
    globalSwitchContainer.style.cssText = `
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        padding: 12px;
        background: white;
        border: 2px solid #4CAF50;
        border-radius: 6px;
        gap: 10px;
    `;
    
    const globalLabel = document.createElement('label');
    globalLabel.innerHTML = '<strong>🔧 Enable Scheduler</strong>';
    globalLabel.style.cssText = 'font-size: 13px; color: #333;';
    
    const globalSwitch = document.createElement('input');
    globalSwitch.type = 'checkbox';
    globalSwitch.checked = globalEnabled;
    globalSwitch.style.cssText = `
        width: 16px;
        height: 16px;
        cursor: pointer;
    `;
    
    const globalStatus = document.createElement('span');
    globalStatus.style.cssText = 'font-size: 11px; font-weight: bold;';
    
    function updateGlobalStatus() {
        globalStatus.textContent = globalEnabled ? '✅ System Active' : '❌ System Disabled';
        globalStatus.style.color = globalEnabled ? '#4CAF50' : '#f44336';
    }
    
    updateGlobalStatus();
    
    globalSwitch.onchange = (e) => {
        globalEnabled = e.target.checked;
        updateGlobalStatus();
        saveSchedules(); // Auto save
    };
    
    globalSwitchContainer.appendChild(globalLabel);
    globalSwitchContainer.appendChild(globalSwitch);
    globalSwitchContainer.appendChild(globalStatus);
    
    // Schedule list container
    const schedulesContainer = document.createElement('div');
    schedulesContainer.style.cssText = 'margin-bottom: 15px;';
    
    function renderSchedules() {
        schedulesContainer.innerHTML = '';
        
        schedules.forEach((schedule, index) => {
            const row = createScheduleRow(schedule, index);
            schedulesContainer.appendChild(row);
        });
    }
    
    // Warning message (if no workflows)
    if (workflows.length === 0) {
        const warning = document.createElement('div');
        warning.innerHTML = `
            <div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; margin-bottom: 12px; font-size: 12px;">
                <strong>⚠️ Warning:</strong> No workflow files found! Please place workflow API-JSON files in <code>ComfyUI-ScheduledTask/Workflow/</code> folder or rightclick save as task. 
            </div>
        `;
        container.appendChild(warning);
    }
    
    // Button container
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = `
        display: flex;
        gap: 8px;
        justify-content: flex-end;
        border-top: 1px solid #ddd;
        padding-top: 12px;
    `;
    
    // Add schedule button
    const addButton = document.createElement('button');
    addButton.textContent = '➕ Add Schedule';
    addButton.style.cssText = `
        padding: 6px 12px;
        background: #2196F3;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
    `;
    
    addButton.onclick = () => {
        schedules.push({
            time: '',
            workflow: '',
            enabled: false
        });
        renderSchedules();
    };
    
    // Save button
    const saveButton = document.createElement('button');
    saveButton.textContent = '💾 Save Settings';
    saveButton.style.cssText = `
        padding: 6px 12px;
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        font-weight: bold;
    `;
    
    saveButton.onclick = async () => {
        saveButton.disabled = true;
        saveButton.textContent = 'Saving...';
        
        await saveSchedules();
        
        saveButton.disabled = false;
        saveButton.textContent = '💾 Save Settings';
    };
    
    buttonContainer.appendChild(addButton);
    buttonContainer.appendChild(saveButton);
    
    // Assemble interface
    container.appendChild(description);
    container.appendChild(globalSwitchContainer);
    container.appendChild(schedulesContainer);
    container.appendChild(buttonContainer);
    
    renderSchedules();
    
    return container;
}

// Create single schedule setting row
function createScheduleRow(schedule, index) {
    const row = document.createElement('div');
    row.style.cssText = `
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        background: white;
        font-size: 12px;
    `;
    
    // Index
    const indexLabel = document.createElement('div');
    indexLabel.textContent = `#${index + 1}`;
    indexLabel.style.cssText = `
        background: #666;
        color: white;
        padding: 4px 8px;
        border-radius: 3px;
        font-weight: bold;
        min-width: 30px;
        text-align: center;
        font-size: 11px;
    `;
    
    // Enable switch
    const enabledContainer = document.createElement('div');
    enabledContainer.style.cssText = 'display: flex; flex-direction: column; align-items: center; gap: 2px;';
    
    const enabledLabel = document.createElement('label');
    enabledLabel.textContent = 'Enable';
    enabledLabel.style.cssText = 'font-size: 10px; color: #666;';
    
    const enabledSwitch = document.createElement('input');
    enabledSwitch.type = 'checkbox';
    enabledSwitch.checked = schedule.enabled || false;
    enabledSwitch.style.cssText = 'width: 13px; height: 13px; cursor: pointer;';
    
    enabledSwitch.onchange = (e) => {
        schedule.enabled = e.target.checked;
        updateRowStyle();
    };
    
    function updateRowStyle() {
        row.style.opacity = schedule.enabled ? '1' : '0.6';
        row.style.background = schedule.enabled ? 'white' : '#f9f9f9';
    }
    
    enabledContainer.appendChild(enabledLabel);
    enabledContainer.appendChild(enabledSwitch);
    
    // Time input
    const timeContainer = document.createElement('div');
    timeContainer.style.cssText = 'display: flex; flex-direction: column; gap: 2px;';
    
    const timeLabel = document.createElement('label');
    timeLabel.textContent = 'Time';
    timeLabel.style.cssText = 'font-size: 10px; color: #666; font-weight: bold;';
    
    const timeInput = document.createElement('input');
    timeInput.type = 'time';
    timeInput.value = schedule.time || '';
    timeInput.style.cssText = `
        padding: 4px;
        border: 1px solid #ccc;
        border-radius: 3px;
        font-size: 11px;
        width: 80px;
    `;
    
    timeInput.onchange = (e) => {
        schedule.time = e.target.value;
    };
    
    timeContainer.appendChild(timeLabel);
    timeContainer.appendChild(timeInput);
    
    // Workflow selection
    const workflowContainer = document.createElement('div');
    workflowContainer.style.cssText = 'display: flex; flex-direction: column; gap: 2px; flex-grow: 1;';
    
    const workflowLabel = document.createElement('label');
    workflowLabel.textContent = 'Workflow File';
    workflowLabel.style.cssText = 'font-size: 10px; color: #666; font-weight: bold;';
    
    const workflowSelect = document.createElement('select');
    workflowSelect.style.cssText = `
        padding: 4px;
        border: 1px solid #ccc;
        border-radius: 3px;
        font-size: 11px;
        background: white;
        width: 100%;
    `;
    
    // Add options
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = '-- Select Workflow File --';
    workflowSelect.appendChild(defaultOption);
    
    workflows.forEach(w => {
        const option = document.createElement('option');
        option.value = w.filename;
        option.textContent = `${w.name} (${w.filename})`;
        if (schedule.workflow === w.filename) {
            option.selected = true;
        }
        workflowSelect.appendChild(option);
    });
    
    workflowSelect.onchange = (e) => {
        schedule.workflow = e.target.value;
    };
    
    workflowContainer.appendChild(workflowLabel);
    workflowContainer.appendChild(workflowSelect);
    
    // Delete button
    const deleteButton = document.createElement('button');
    deleteButton.textContent = '❌';
    deleteButton.title = 'Delete this schedule';
    deleteButton.style.cssText = `
        background: #f44336;
        color: white;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        padding: 4px 6px;
        font-size: 10px;
    `;
    
    deleteButton.onclick = () => {
        if (confirm('Are you sure you want to delete this schedule?')) {
            schedules.splice(index, 1);
            // Re-render entire list
            const container = row.parentElement;
            container.innerHTML = '';
            schedules.forEach((s, i) => {
                const newRow = createScheduleRow(s, i);
                container.appendChild(newRow);
            });
        }
    };
    
    // Assemble row
    row.appendChild(indexLabel);
    row.appendChild(enabledContainer);
    row.appendChild(timeContainer);
    row.appendChild(workflowContainer);
    row.appendChild(deleteButton);
    
    updateRowStyle();
    
    return row;
}

// Check if ComfyUI is loaded
function waitForComfyUI() {
    return new Promise((resolve) => {
        if (app) {
            resolve();
        } else {
            const checkInterval = setInterval(() => {
                if (window.app) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 100);
        }
    });
}

// Register extension
waitForComfyUI().then(() => {
    console.log("🔧 Starting to register ComfyUI-ScheduledTask extension");
    
    app.registerExtension({
        name: "ComfyUI-ScheduledTask",
        
        settings: [
            {
                id: "ScheduledTask.ScheduledTask",
                name: "🎨",
                type: () => {
                    console.log("🎨 Creating schedule settings interface");
                    
                    if (!settingsContainer) {
                        // Create loading container
                        settingsContainer = document.createElement('div');
                        settingsContainer.innerHTML = '<div style="padding: 15px; text-align: center; font-size: 12px;">Loading schedule settings...</div>';
                        
                        // Load actual content asynchronously
                        createScheduleSettings().then(content => {
                            settingsContainer.innerHTML = '';
                            settingsContainer.appendChild(content);
                            console.log("✅ Schedule settings interface loaded successfully");
                        }).catch(error => {
                            console.error("❌ Failed to load schedule settings interface:", error);
                            settingsContainer.innerHTML = `<div style="padding: 15px; color: red; font-size: 12px;">Loading failed: ${error.message}</div>`;
                        });
                    }
                    return settingsContainer;
                },
                defaultValue: true,
                tooltip: "Configure and manage workflow scheduling tasks"
            }
        ],
        
        async setup() {
            console.log("✅ ComfyUI-ScheduledTask extension loaded");
            
            // Add context menu item
            const origGetCanvasMenuOptions = LGraphCanvas.prototype.getCanvasMenuOptions;
            LGraphCanvas.prototype.getCanvasMenuOptions = function () {
                const options = origGetCanvasMenuOptions.apply(this, arguments);
                
                // Add separator
                options.push(null);
                
                // Add our menu item
                options.push({
                    content: "📋 Save as Task",
                    callback: () => {
                        saveWorkflowAsTask();
                    }
                });
                
                return options;
            };
        }
    });
}).catch(error => {
    console.error("❌ Failed to register ComfyUI-ScheduledTask extension:", error);
});