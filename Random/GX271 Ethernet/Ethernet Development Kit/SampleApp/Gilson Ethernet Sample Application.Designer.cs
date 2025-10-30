namespace Gilson.EthernetSample
{
    partial class SampleApplication
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();

                if (udpListener != null)
                {
                    udpListener.Stop();
                    udpListener = null;
                }

                if (bindingSource != null)
                {
                    bindingSource.Dispose();
                    bindingSource = null;
                }

                if (tblCmdParam != null)
                {
                    tblCmdParam.Dispose();
                    tblCmdParam = null;
                }

                if(socketList != null)
                {
                    socketList.Clear();
                    socketList = null;
                }

                if(treeInstruments != null)
                {
                    treeInstruments.Nodes.Clear();
                    treeInstruments = null;
                }
                currentInstrument = null;
            }

            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(SampleApplication));
            System.Windows.Forms.ListViewItem listViewItem1 = new System.Windows.Forms.ListViewItem(new string[] {
            "IP Address",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem2 = new System.Windows.Forms.ListViewItem(new string[] {
            "Port",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem3 = new System.Windows.Forms.ListViewItem(new string[] {
            "GSIOC ID",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem4 = new System.Windows.Forms.ListViewItem(new string[] {
            "Serial Number",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem5 = new System.Windows.Forms.ListViewItem(new string[] {
            "Instructionset Version",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem6 = new System.Windows.Forms.ListViewItem(new string[] {
            "Instructionset Name",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem7 = new System.Windows.Forms.ListViewItem(new string[] {
            "System Version",
            "",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem8 = new System.Windows.Forms.ListViewItem(new string[] {
            "Firmware Version",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem9 = new System.Windows.Forms.ListViewItem(new string[] {
            "PROM Version",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem10 = new System.Windows.Forms.ListViewItem(new string[] {
            "Instructionset Group",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem11 = new System.Windows.Forms.ListViewItem(new string[] {
            "Lease Acquired Time",
            ""}, -1);
            System.Windows.Forms.ListViewItem listViewItem12 = new System.Windows.Forms.ListViewItem(new string[] {
            "Lease Expires in(secs)",
            ""}, -1);
            this.dataGridCommandParams = new System.Windows.Forms.DataGridView();
            this.ctxDevcieCommunication = new System.Windows.Forms.ContextMenuStrip(this.components);
            this.connectToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.disconnectToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator3 = new System.Windows.Forms.ToolStripSeparator();
            this.setAsAdminToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripMenuItemGetInstructionSet = new System.Windows.Forms.ToolStripMenuItem();
            this.systemToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.renewLeaseToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.dropLeaseToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator1 = new System.Windows.Forms.ToolStripSeparator();
            this.getFirmwareVersionToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator2 = new System.Windows.Forms.ToolStripSeparator();
            this.getLastResponseToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripSeparator4 = new System.Windows.Forms.ToolStripSeparator();
            this.instrumentImages = new System.Windows.Forms.ImageList(this.components);
            this.ctxVisibleColumns = new System.Windows.Forms.ContextMenuStrip(this.components);
            this.mnuDeviceName = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuIPAddress = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuDeviceID = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuGUID = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuSerialNumber = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuISVersion = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuISName = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuSysVersion = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuFWVersion = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuPromVersion = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuISGroup = new System.Windows.Forms.ToolStripMenuItem();
            this.mnuLease = new System.Windows.Forms.ToolStripMenuItem();
            this.btnDelete = new System.Windows.Forms.Button();
            this.btnAdd = new System.Windows.Forms.Button();
            this.lblExecutionList = new System.Windows.Forms.Label();
            this.treeExecutionList = new System.Windows.Forms.TreeView();
            this.ctxExecutionList = new System.Windows.Forms.ContextMenuStrip(this.components);
            this.executeToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.updateSequenceToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.deleteToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.clearToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.lblCommands = new System.Windows.Forms.Label();
            this.cmbCommands = new System.Windows.Forms.ComboBox();
            this.treeInstruments = new System.Windows.Forms.TreeView();
            this.lblInstruments = new System.Windows.Forms.Label();
            this.splitContainer1 = new System.Windows.Forms.SplitContainer();
            this.lstInstrumentProps = new System.Windows.Forms.ListView();
            this.clmPropertyName = new System.Windows.Forms.ColumnHeader();
            this.clmPropertyValue = new System.Windows.Forms.ColumnHeader();
            this.splitter1 = new System.Windows.Forms.Splitter();
            this.splitContainer2 = new System.Windows.Forms.SplitContainer();
            this.btnExecute = new System.Windows.Forms.Button();
            this.lstCommands = new System.Windows.Forms.ListView();
            this.clmTime = new System.Windows.Forms.ColumnHeader();
            this.clmSeq = new System.Windows.Forms.ColumnHeader();
            this.clmID = new System.Windows.Forms.ColumnHeader();
            this.clmInstrument = new System.Windows.Forms.ColumnHeader();
            this.clmCommand = new System.Windows.Forms.ColumnHeader();
            this.clmStatus = new System.Windows.Forms.ColumnHeader();
            this.clmReturnValues = new System.Windows.Forms.ColumnHeader();
            this.ctxCommandResponseList = new System.Windows.Forms.ContextMenuStrip(this.components);
            this.clearToolStripMenuItem1 = new System.Windows.Forms.ToolStripMenuItem();
            this.splitContainer3 = new System.Windows.Forms.SplitContainer();
            ((System.ComponentModel.ISupportInitialize)(this.dataGridCommandParams)).BeginInit();
            this.ctxDevcieCommunication.SuspendLayout();
            this.ctxVisibleColumns.SuspendLayout();
            this.ctxExecutionList.SuspendLayout();
            this.splitContainer1.Panel1.SuspendLayout();
            this.splitContainer1.Panel2.SuspendLayout();
            this.splitContainer1.SuspendLayout();
            this.splitContainer2.Panel1.SuspendLayout();
            this.splitContainer2.Panel2.SuspendLayout();
            this.splitContainer2.SuspendLayout();
            this.ctxCommandResponseList.SuspendLayout();
            this.splitContainer3.Panel1.SuspendLayout();
            this.splitContainer3.Panel2.SuspendLayout();
            this.splitContainer3.SuspendLayout();
            this.SuspendLayout();
            // 
            // dataGridCommandParams
            // 
            this.dataGridCommandParams.AllowUserToAddRows = false;
            this.dataGridCommandParams.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            this.dataGridCommandParams.Location = new System.Drawing.Point(7, 36);
            this.dataGridCommandParams.Name = "dataGridCommandParams";
            this.dataGridCommandParams.Size = new System.Drawing.Size(403, 95);
            this.dataGridCommandParams.TabIndex = 4;
            // 
            // ctxDevcieCommunication
            // 
            this.ctxDevcieCommunication.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.connectToolStripMenuItem,
            this.disconnectToolStripMenuItem,
            this.toolStripSeparator3,
            this.setAsAdminToolStripMenuItem,
            this.toolStripMenuItemGetInstructionSet,
            this.systemToolStripMenuItem,
            this.toolStripSeparator4});
            this.ctxDevcieCommunication.Name = "ctxDevcieCommunication";
            this.ctxDevcieCommunication.Size = new System.Drawing.Size(172, 126);
            this.ctxDevcieCommunication.Opening += new System.ComponentModel.CancelEventHandler(this.ctxDevcieCommunicationOpening);
            // 
            // connectToolStripMenuItem
            // 
            this.connectToolStripMenuItem.Name = "connectToolStripMenuItem";
            this.connectToolStripMenuItem.Size = new System.Drawing.Size(171, 22);
            this.connectToolStripMenuItem.Text = "Connect";
            this.connectToolStripMenuItem.Click += new System.EventHandler(this.connectToolStripMenuItemClick);
            // 
            // disconnectToolStripMenuItem
            // 
            this.disconnectToolStripMenuItem.Name = "disconnectToolStripMenuItem";
            this.disconnectToolStripMenuItem.Size = new System.Drawing.Size(171, 22);
            this.disconnectToolStripMenuItem.Text = "Disconnect";
            this.disconnectToolStripMenuItem.Click += new System.EventHandler(this.disconnectToolStripMenuItemClick);
            // 
            // toolStripSeparator3
            // 
            this.toolStripSeparator3.Name = "toolStripSeparator3";
            this.toolStripSeparator3.Size = new System.Drawing.Size(168, 6);
            // 
            // setAsAdminToolStripMenuItem
            // 
            this.setAsAdminToolStripMenuItem.Name = "setAsAdminToolStripMenuItem";
            this.setAsAdminToolStripMenuItem.Size = new System.Drawing.Size(171, 22);
            this.setAsAdminToolStripMenuItem.Text = "Set As Admin";
            this.setAsAdminToolStripMenuItem.Click += new System.EventHandler(this.getVersionsAsAdminToolStripMenuItemClick);
            // 
            // toolStripMenuItemGetInstructionSet
            // 
            this.toolStripMenuItemGetInstructionSet.Name = "toolStripMenuItemGetInstructionSet";
            this.toolStripMenuItemGetInstructionSet.Size = new System.Drawing.Size(171, 22);
            this.toolStripMenuItemGetInstructionSet.Text = "Get Instruction Set";
            this.toolStripMenuItemGetInstructionSet.Click += new System.EventHandler(this.toolStripMenuItemGetInstructionSetClick);
            // 
            // systemToolStripMenuItem
            // 
            this.systemToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.renewLeaseToolStripMenuItem,
            this.dropLeaseToolStripMenuItem,
            this.toolStripSeparator1,
            this.getFirmwareVersionToolStripMenuItem,
            this.toolStripSeparator2,
            this.getLastResponseToolStripMenuItem});
            this.systemToolStripMenuItem.Name = "systemToolStripMenuItem";
            this.systemToolStripMenuItem.Size = new System.Drawing.Size(171, 22);
            this.systemToolStripMenuItem.Text = "System";
            // 
            // renewLeaseToolStripMenuItem
            // 
            this.renewLeaseToolStripMenuItem.Name = "renewLeaseToolStripMenuItem";
            this.renewLeaseToolStripMenuItem.Size = new System.Drawing.Size(186, 22);
            this.renewLeaseToolStripMenuItem.Text = "Renew Lease";
            this.renewLeaseToolStripMenuItem.Click += new System.EventHandler(this.renewLeaseToolStripMenuItemClick);
            // 
            // dropLeaseToolStripMenuItem
            // 
            this.dropLeaseToolStripMenuItem.Name = "dropLeaseToolStripMenuItem";
            this.dropLeaseToolStripMenuItem.Size = new System.Drawing.Size(186, 22);
            this.dropLeaseToolStripMenuItem.Text = "Drop Lease";
            this.dropLeaseToolStripMenuItem.Click += new System.EventHandler(this.dropLeaseToolStripMenuItemClick);
            // 
            // toolStripSeparator1
            // 
            this.toolStripSeparator1.Name = "toolStripSeparator1";
            this.toolStripSeparator1.Size = new System.Drawing.Size(183, 6);
            // 
            // getFirmwareVersionToolStripMenuItem
            // 
            this.getFirmwareVersionToolStripMenuItem.Name = "getFirmwareVersionToolStripMenuItem";
            this.getFirmwareVersionToolStripMenuItem.Size = new System.Drawing.Size(186, 22);
            this.getFirmwareVersionToolStripMenuItem.Text = "Get Firmware Version";
            this.getFirmwareVersionToolStripMenuItem.Click += new System.EventHandler(this.getFirmwareVersionToolStripMenuItemClick);
            // 
            // toolStripSeparator2
            // 
            this.toolStripSeparator2.Name = "toolStripSeparator2";
            this.toolStripSeparator2.Size = new System.Drawing.Size(183, 6);
            // 
            // getLastResponseToolStripMenuItem
            // 
            this.getLastResponseToolStripMenuItem.Name = "getLastResponseToolStripMenuItem";
            this.getLastResponseToolStripMenuItem.Size = new System.Drawing.Size(186, 22);
            this.getLastResponseToolStripMenuItem.Text = "Get Last Response";
            this.getLastResponseToolStripMenuItem.Click += new System.EventHandler(this.getLastResponseToolStripMenuItemClick);
            // 
            // toolStripSeparator4
            // 
            this.toolStripSeparator4.Name = "toolStripSeparator4";
            this.toolStripSeparator4.Size = new System.Drawing.Size(168, 6);
            // 
            // instrumentImages
            // 
            this.instrumentImages.ImageStream = ((System.Windows.Forms.ImageListStreamer)(resources.GetObject("instrumentImages.ImageStream")));
            this.instrumentImages.TransparentColor = System.Drawing.Color.Transparent;
            this.instrumentImages.Images.SetKeyName(0, "");
            this.instrumentImages.Images.SetKeyName(1, "");
            this.instrumentImages.Images.SetKeyName(2, "");
            // 
            // ctxVisibleColumns
            // 
            this.ctxVisibleColumns.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.mnuDeviceName,
            this.mnuIPAddress,
            this.mnuDeviceID,
            this.mnuGUID,
            this.mnuSerialNumber,
            this.mnuISVersion,
            this.mnuISName,
            this.mnuSysVersion,
            this.mnuFWVersion,
            this.mnuPromVersion,
            this.mnuISGroup,
            this.mnuLease});
            this.ctxVisibleColumns.Name = "ctxVisibleColumns";
            this.ctxVisibleColumns.ShowCheckMargin = true;
            this.ctxVisibleColumns.Size = new System.Drawing.Size(173, 268);
            // 
            // mnuDeviceName
            // 
            this.mnuDeviceName.Name = "mnuDeviceName";
            this.mnuDeviceName.Size = new System.Drawing.Size(172, 22);
            this.mnuDeviceName.Text = "Device Name";
            // 
            // mnuIPAddress
            // 
            this.mnuIPAddress.Name = "mnuIPAddress";
            this.mnuIPAddress.Size = new System.Drawing.Size(172, 22);
            this.mnuIPAddress.Text = "IP Address";
            // 
            // mnuDeviceID
            // 
            this.mnuDeviceID.Name = "mnuDeviceID";
            this.mnuDeviceID.Size = new System.Drawing.Size(172, 22);
            this.mnuDeviceID.Text = "Device ID";
            // 
            // mnuGUID
            // 
            this.mnuGUID.Name = "mnuGUID";
            this.mnuGUID.Size = new System.Drawing.Size(172, 22);
            this.mnuGUID.Text = "GUID";
            // 
            // mnuSerialNumber
            // 
            this.mnuSerialNumber.Name = "mnuSerialNumber";
            this.mnuSerialNumber.Size = new System.Drawing.Size(172, 22);
            this.mnuSerialNumber.Text = "Serial Number";
            // 
            // mnuISVersion
            // 
            this.mnuISVersion.Name = "mnuISVersion";
            this.mnuISVersion.Size = new System.Drawing.Size(172, 22);
            this.mnuISVersion.Text = "IS Version";
            // 
            // mnuISName
            // 
            this.mnuISName.Name = "mnuISName";
            this.mnuISName.Size = new System.Drawing.Size(172, 22);
            this.mnuISName.Text = "IS Name";
            // 
            // mnuSysVersion
            // 
            this.mnuSysVersion.Name = "mnuSysVersion";
            this.mnuSysVersion.Size = new System.Drawing.Size(172, 22);
            this.mnuSysVersion.Text = "Sys Version";
            // 
            // mnuFWVersion
            // 
            this.mnuFWVersion.Name = "mnuFWVersion";
            this.mnuFWVersion.Size = new System.Drawing.Size(172, 22);
            this.mnuFWVersion.Text = "FW Version";
            // 
            // mnuPromVersion
            // 
            this.mnuPromVersion.Name = "mnuPromVersion";
            this.mnuPromVersion.Size = new System.Drawing.Size(172, 22);
            this.mnuPromVersion.Text = "PROM Version";
            // 
            // mnuISGroup
            // 
            this.mnuISGroup.Name = "mnuISGroup";
            this.mnuISGroup.Size = new System.Drawing.Size(172, 22);
            this.mnuISGroup.Text = "IS Group";
            // 
            // mnuLease
            // 
            this.mnuLease.Name = "mnuLease";
            this.mnuLease.Size = new System.Drawing.Size(172, 22);
            this.mnuLease.Text = "Lease";
            // 
            // btnDelete
            // 
            this.btnDelete.AutoSize = true;
            this.btnDelete.Location = new System.Drawing.Point(416, 77);
            this.btnDelete.Name = "btnDelete";
            this.btnDelete.Size = new System.Drawing.Size(59, 23);
            this.btnDelete.TabIndex = 6;
            this.btnDelete.Text = "<<";
            this.btnDelete.UseVisualStyleBackColor = true;
            this.btnDelete.Click += new System.EventHandler(this.btnDeleteClick);
            // 
            // btnAdd
            // 
            this.btnAdd.AutoSize = true;
            this.btnAdd.Location = new System.Drawing.Point(416, 36);
            this.btnAdd.Name = "btnAdd";
            this.btnAdd.Size = new System.Drawing.Size(59, 23);
            this.btnAdd.TabIndex = 5;
            this.btnAdd.Text = ">>";
            this.btnAdd.UseVisualStyleBackColor = true;
            this.btnAdd.Click += new System.EventHandler(this.btnAddClick);
            // 
            // lblExecutionList
            // 
            this.lblExecutionList.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left)
                        | System.Windows.Forms.AnchorStyles.Right)));
            this.lblExecutionList.AutoSize = true;
            this.lblExecutionList.Location = new System.Drawing.Point(478, 3);
            this.lblExecutionList.Name = "lblExecutionList";
            this.lblExecutionList.Size = new System.Drawing.Size(85, 13);
            this.lblExecutionList.TabIndex = 3;
            this.lblExecutionList.Text = "Execution List";
            // 
            // treeExecutionList
            // 
            this.treeExecutionList.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left)
                        | System.Windows.Forms.AnchorStyles.Right)));
            this.treeExecutionList.CheckBoxes = true;
            this.treeExecutionList.ContextMenuStrip = this.ctxExecutionList;
            this.treeExecutionList.Location = new System.Drawing.Point(481, 19);
            this.treeExecutionList.Name = "treeExecutionList";
            this.treeExecutionList.ShowLines = false;
            this.treeExecutionList.ShowPlusMinus = false;
            this.treeExecutionList.ShowRootLines = false;
            this.treeExecutionList.Size = new System.Drawing.Size(462, 112);
            this.treeExecutionList.TabIndex = 2;
            // 
            // ctxExecutionList
            // 
            this.ctxExecutionList.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.executeToolStripMenuItem,
            this.updateSequenceToolStripMenuItem,
            this.deleteToolStripMenuItem,
            this.clearToolStripMenuItem});
            this.ctxExecutionList.Name = "ctxExecutionList";
            this.ctxExecutionList.Size = new System.Drawing.Size(219, 92);
            // 
            // executeToolStripMenuItem
            // 
            this.executeToolStripMenuItem.Name = "executeToolStripMenuItem";
            this.executeToolStripMenuItem.Size = new System.Drawing.Size(218, 22);
            this.executeToolStripMenuItem.Text = "Execute";
            this.executeToolStripMenuItem.Click += new System.EventHandler(this.executeToolStripMenuItemClick);
            // 
            // updateSequenceToolStripMenuItem
            // 
            this.updateSequenceToolStripMenuItem.Name = "updateSequenceToolStripMenuItem";
            this.updateSequenceToolStripMenuItem.Size = new System.Drawing.Size(218, 22);
            this.updateSequenceToolStripMenuItem.Text = "Update Sequence Numbers";
            this.updateSequenceToolStripMenuItem.Click += new System.EventHandler(this.updateSequenceToolStripMenuItemClick);
            // 
            // deleteToolStripMenuItem
            // 
            this.deleteToolStripMenuItem.Name = "deleteToolStripMenuItem";
            this.deleteToolStripMenuItem.Size = new System.Drawing.Size(218, 22);
            this.deleteToolStripMenuItem.Text = "Delete";
            this.deleteToolStripMenuItem.Click += new System.EventHandler(this.deleteToolStripMenuItemClick);
            // 
            // clearToolStripMenuItem
            // 
            this.clearToolStripMenuItem.Name = "clearToolStripMenuItem";
            this.clearToolStripMenuItem.Size = new System.Drawing.Size(218, 22);
            this.clearToolStripMenuItem.Text = "Clear";
            this.clearToolStripMenuItem.Click += new System.EventHandler(this.clearToolStripMenuItemClick);
            // 
            // lblCommands
            // 
            this.lblCommands.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left)
                        | System.Windows.Forms.AnchorStyles.Right)));
            this.lblCommands.AutoSize = true;
            this.lblCommands.Location = new System.Drawing.Point(7, 2);
            this.lblCommands.Name = "lblCommands";
            this.lblCommands.Size = new System.Drawing.Size(72, 13);
            this.lblCommands.TabIndex = 1;
            this.lblCommands.Text = "Commands";
            // 
            // cmbCommands
            // 
            this.cmbCommands.FormattingEnabled = true;
            this.cmbCommands.Location = new System.Drawing.Point(7, 15);
            this.cmbCommands.Name = "cmbCommands";
            this.cmbCommands.Size = new System.Drawing.Size(403, 21);
            this.cmbCommands.TabIndex = 0;
            this.cmbCommands.SelectedIndexChanged += new System.EventHandler(this.cmbCommandsSelectedIndexChanged);
            // 
            // treeInstruments
            // 
            this.treeInstruments.ContextMenuStrip = this.ctxDevcieCommunication;
            this.treeInstruments.Dock = System.Windows.Forms.DockStyle.Fill;
            this.treeInstruments.Location = new System.Drawing.Point(0, 0);
            this.treeInstruments.Name = "treeInstruments";
            this.treeInstruments.Size = new System.Drawing.Size(496, 218);
            this.treeInstruments.TabIndex = 4;
            this.treeInstruments.AfterSelect += new System.Windows.Forms.TreeViewEventHandler(this.treeInstrumentsAfterSelect);
            // 
            // lblInstruments
            // 
            this.lblInstruments.AutoSize = true;
            this.lblInstruments.Location = new System.Drawing.Point(3, 0);
            this.lblInstruments.Name = "lblInstruments";
            this.lblInstruments.Size = new System.Drawing.Size(76, 13);
            this.lblInstruments.TabIndex = 1;
            this.lblInstruments.Text = "Instruments";
            // 
            // splitContainer1
            // 
            this.splitContainer1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.splitContainer1.Location = new System.Drawing.Point(0, 0);
            this.splitContainer1.Name = "splitContainer1";
            // 
            // splitContainer1.Panel1
            // 
            this.splitContainer1.Panel1.Controls.Add(this.treeInstruments);
            // 
            // splitContainer1.Panel2
            // 
            this.splitContainer1.Panel2.Controls.Add(this.lstInstrumentProps);
            this.splitContainer1.Size = new System.Drawing.Size(946, 218);
            this.splitContainer1.SplitterDistance = 496;
            this.splitContainer1.TabIndex = 5;
            // 
            // lstInstrumentProps
            // 
            this.lstInstrumentProps.Columns.AddRange(new System.Windows.Forms.ColumnHeader[] {
            this.clmPropertyName,
            this.clmPropertyValue});
            this.lstInstrumentProps.Dock = System.Windows.Forms.DockStyle.Fill;
            listViewItem1.ToolTipText = "IP Address of the Ethernet Instrument";
            listViewItem2.ToolTipText = "Port at which ethernet instrument is connected to.";
            listViewItem3.ToolTipText = "Unique ID of the instrument on GSIOC bus.";
            listViewItem4.ToolTipText = "Serial Number of the instrument.";
            listViewItem5.ToolTipText = "Version number of the instruction set fro the instrument.";
            listViewItem6.ToolTipText = "Name of the instructionset for the instrument.";
            listViewItem8.ToolTipText = "Firmware Version of the instrument.";
            listViewItem9.ToolTipText = "PROM version of the instrument.";
            listViewItem10.ToolTipText = "Group of devices associated with the  instruction set";
            listViewItem11.ToolTipText = "Lease Acquired DateTime";
            listViewItem12.ToolTipText = "Lease Expiration DateTime";
            this.lstInstrumentProps.Items.AddRange(new System.Windows.Forms.ListViewItem[] {
            listViewItem1,
            listViewItem2,
            listViewItem3,
            listViewItem4,
            listViewItem5,
            listViewItem6,
            listViewItem7,
            listViewItem8,
            listViewItem9,
            listViewItem10,
            listViewItem11,
            listViewItem12});
            this.lstInstrumentProps.Location = new System.Drawing.Point(0, 0);
            this.lstInstrumentProps.Name = "lstInstrumentProps";
            this.lstInstrumentProps.Size = new System.Drawing.Size(446, 218);
            this.lstInstrumentProps.TabIndex = 0;
            this.lstInstrumentProps.UseCompatibleStateImageBehavior = false;
            this.lstInstrumentProps.View = System.Windows.Forms.View.Details;
            // 
            // clmPropertyName
            // 
            this.clmPropertyName.Text = "Property";
            this.clmPropertyName.Width = 182;
            // 
            // clmPropertyValue
            // 
            this.clmPropertyValue.Text = "Value";
            this.clmPropertyValue.Width = 278;
            // 
            // splitter1
            // 
            this.splitter1.Location = new System.Drawing.Point(0, 0);
            this.splitter1.Name = "splitter1";
            this.splitter1.Size = new System.Drawing.Size(3, 639);
            this.splitter1.TabIndex = 2;
            this.splitter1.TabStop = false;
            // 
            // splitContainer2
            // 
            this.splitContainer2.Dock = System.Windows.Forms.DockStyle.Fill;
            this.splitContainer2.Location = new System.Drawing.Point(0, 0);
            this.splitContainer2.Name = "splitContainer2";
            this.splitContainer2.Orientation = System.Windows.Forms.Orientation.Horizontal;
            // 
            // splitContainer2.Panel1
            // 
            this.splitContainer2.Panel1.Controls.Add(this.splitContainer1);
            // 
            // splitContainer2.Panel2
            // 
            this.splitContainer2.Panel2.Controls.Add(this.btnExecute);
            this.splitContainer2.Panel2.Controls.Add(this.dataGridCommandParams);
            this.splitContainer2.Panel2.Controls.Add(this.lblExecutionList);
            this.splitContainer2.Panel2.Controls.Add(this.treeExecutionList);
            this.splitContainer2.Panel2.Controls.Add(this.btnDelete);
            this.splitContainer2.Panel2.Controls.Add(this.cmbCommands);
            this.splitContainer2.Panel2.Controls.Add(this.btnAdd);
            this.splitContainer2.Panel2.Controls.Add(this.lblCommands);
            this.splitContainer2.Size = new System.Drawing.Size(946, 391);
            this.splitContainer2.SplitterDistance = 218;
            this.splitContainer2.TabIndex = 7;
            // 
            // btnExecute
            // 
            this.btnExecute.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right)));
            this.btnExecute.Location = new System.Drawing.Point(835, 132);
            this.btnExecute.Name = "btnExecute";
            this.btnExecute.Size = new System.Drawing.Size(108, 23);
            this.btnExecute.TabIndex = 7;
            this.btnExecute.Text = "Execute";
            this.btnExecute.UseVisualStyleBackColor = true;
            this.btnExecute.Click += new System.EventHandler(this.btnExecuteClick);
            // 
            // lstCommands
            // 
            this.lstCommands.Columns.AddRange(new System.Windows.Forms.ColumnHeader[] {
            this.clmTime,
            this.clmSeq,
            this.clmID,
            this.clmInstrument,
            this.clmCommand,
            this.clmStatus,
            this.clmReturnValues});
            this.lstCommands.ContextMenuStrip = this.ctxCommandResponseList;
            this.lstCommands.Dock = System.Windows.Forms.DockStyle.Fill;
            this.lstCommands.FullRowSelect = true;
            this.lstCommands.Location = new System.Drawing.Point(0, 0);
            this.lstCommands.Name = "lstCommands";
            this.lstCommands.ShowItemToolTips = true;
            this.lstCommands.Size = new System.Drawing.Size(946, 244);
            this.lstCommands.TabIndex = 8;
            this.lstCommands.UseCompatibleStateImageBehavior = false;
            this.lstCommands.View = System.Windows.Forms.View.Details;
            // 
            // clmTime
            // 
            this.clmTime.Text = "Time";
            this.clmTime.Width = 62;
            // 
            // clmSeq
            // 
            this.clmSeq.Text = "Seq";
            this.clmSeq.Width = 56;
            // 
            // clmID
            // 
            this.clmID.Text = "ID";
            this.clmID.Width = 41;
            // 
            // clmInstrument
            // 
            this.clmInstrument.Text = "Instrument";
            this.clmInstrument.Width = 123;
            // 
            // clmCommand
            // 
            this.clmCommand.Text = "Command";
            this.clmCommand.Width = 212;
            // 
            // clmStatus
            // 
            this.clmStatus.Text = "Status";
            this.clmStatus.Width = 89;
            // 
            // clmReturnValues
            // 
            this.clmReturnValues.Text = "Return Values";
            this.clmReturnValues.Width = 175;
            // 
            // ctxCommandResponseList
            // 
            this.ctxCommandResponseList.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.clearToolStripMenuItem1});
            this.ctxCommandResponseList.Name = "ctxCommandResponseList";
            this.ctxCommandResponseList.Size = new System.Drawing.Size(102, 26);
            // 
            // clearToolStripMenuItem1
            // 
            this.clearToolStripMenuItem1.Name = "clearToolStripMenuItem1";
            this.clearToolStripMenuItem1.Size = new System.Drawing.Size(101, 22);
            this.clearToolStripMenuItem1.Text = "Clear";
            this.clearToolStripMenuItem1.Click += new System.EventHandler(this.clearToolStripMenuItem1Click);
            // 
            // splitContainer3
            // 
            this.splitContainer3.Dock = System.Windows.Forms.DockStyle.Fill;
            this.splitContainer3.Location = new System.Drawing.Point(3, 0);
            this.splitContainer3.Name = "splitContainer3";
            this.splitContainer3.Orientation = System.Windows.Forms.Orientation.Horizontal;
            // 
            // splitContainer3.Panel1
            // 
            this.splitContainer3.Panel1.Controls.Add(this.splitContainer2);
            // 
            // splitContainer3.Panel2
            // 
            this.splitContainer3.Panel2.Controls.Add(this.lstCommands);
            this.splitContainer3.Size = new System.Drawing.Size(946, 639);
            this.splitContainer3.SplitterDistance = 391;
            this.splitContainer3.TabIndex = 9;
            // 
            // SampleApplication
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(7F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(949, 639);
            this.Controls.Add(this.splitContainer3);
            this.Controls.Add(this.lblInstruments);
            this.Controls.Add(this.splitter1);
            this.Font = new System.Drawing.Font("Verdana", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.Name = "SampleApplication";
            this.Text = "Gilson Ethernet Sample Application";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.frmMainFormClosing);
            ((System.ComponentModel.ISupportInitialize)(this.dataGridCommandParams)).EndInit();
            this.ctxDevcieCommunication.ResumeLayout(false);
            this.ctxVisibleColumns.ResumeLayout(false);
            this.ctxExecutionList.ResumeLayout(false);
            this.splitContainer1.Panel1.ResumeLayout(false);
            this.splitContainer1.Panel2.ResumeLayout(false);
            this.splitContainer1.ResumeLayout(false);
            this.splitContainer2.Panel1.ResumeLayout(false);
            this.splitContainer2.Panel2.ResumeLayout(false);
            this.splitContainer2.Panel2.PerformLayout();
            this.splitContainer2.ResumeLayout(false);
            this.ctxCommandResponseList.ResumeLayout(false);
            this.splitContainer3.Panel1.ResumeLayout(false);
            this.splitContainer3.Panel2.ResumeLayout(false);
            this.splitContainer3.ResumeLayout(false);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.ContextMenuStrip ctxVisibleColumns;
        private System.Windows.Forms.ToolStripMenuItem mnuDeviceName;
        private System.Windows.Forms.ToolStripMenuItem mnuIPAddress;
        private System.Windows.Forms.ToolStripMenuItem mnuDeviceID;
        private System.Windows.Forms.ToolStripMenuItem mnuGUID;
        private System.Windows.Forms.ToolStripMenuItem mnuSerialNumber;
        private System.Windows.Forms.ToolStripMenuItem mnuISVersion;
        private System.Windows.Forms.ToolStripMenuItem mnuISName;
        private System.Windows.Forms.ToolStripMenuItem mnuSysVersion;
        private System.Windows.Forms.ToolStripMenuItem mnuFWVersion;
        private System.Windows.Forms.ToolStripMenuItem mnuPromVersion;
        private System.Windows.Forms.ToolStripMenuItem mnuISGroup;
        private System.Windows.Forms.ToolStripMenuItem mnuLease;
        private System.Windows.Forms.Label lblCommands;
        private System.Windows.Forms.ComboBox cmbCommands;
        private System.Windows.Forms.Label lblExecutionList;
        private System.Windows.Forms.TreeView treeExecutionList;
        private System.Windows.Forms.ContextMenuStrip ctxDevcieCommunication;
        private System.Windows.Forms.ToolStripMenuItem connectToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem setAsAdminToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem systemToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem renewLeaseToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem dropLeaseToolStripMenuItem;
        private System.Windows.Forms.ToolStripSeparator toolStripSeparator1;
        private System.Windows.Forms.ToolStripMenuItem getFirmwareVersionToolStripMenuItem;
        private System.Windows.Forms.ToolStripSeparator toolStripSeparator2;
        private System.Windows.Forms.ToolStripMenuItem getLastResponseToolStripMenuItem;
        private System.Windows.Forms.Button btnDelete;
        private System.Windows.Forms.Button btnAdd;
        private System.Windows.Forms.ContextMenuStrip ctxExecutionList;
        private System.Windows.Forms.ToolStripMenuItem executeToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem updateSequenceToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem deleteToolStripMenuItem;
        private System.Windows.Forms.DataGridView dataGridCommandParams;
        private System.Windows.Forms.ImageList instrumentImages;
        private System.Windows.Forms.ToolStripMenuItem disconnectToolStripMenuItem;
        private System.Windows.Forms.ToolStripSeparator toolStripSeparator3;
        private System.Windows.Forms.ToolStripSeparator toolStripSeparator4;
        private System.Windows.Forms.TreeView treeInstruments;
        private System.Windows.Forms.Label lblInstruments;
        private System.Windows.Forms.SplitContainer splitContainer1;
        private System.Windows.Forms.ListView lstInstrumentProps;
        private System.Windows.Forms.ColumnHeader clmPropertyName;
        private System.Windows.Forms.ColumnHeader clmPropertyValue;
        private System.Windows.Forms.ToolStripMenuItem toolStripMenuItemGetInstructionSet;
        private System.Windows.Forms.Splitter splitter1;
        private System.Windows.Forms.SplitContainer splitContainer2;
        private System.Windows.Forms.Button btnExecute;
        private System.Windows.Forms.ListView lstCommands;
        private System.Windows.Forms.SplitContainer splitContainer3;
        private System.Windows.Forms.ColumnHeader clmTime;
        private System.Windows.Forms.ColumnHeader clmSeq;
        private System.Windows.Forms.ColumnHeader clmID;
        private System.Windows.Forms.ColumnHeader clmInstrument;
        private System.Windows.Forms.ColumnHeader clmCommand;
        private System.Windows.Forms.ColumnHeader clmStatus;
        private System.Windows.Forms.ColumnHeader clmReturnValues;
        private System.Windows.Forms.ToolStripMenuItem clearToolStripMenuItem;
        private System.Windows.Forms.ContextMenuStrip ctxCommandResponseList;
        private System.Windows.Forms.ToolStripMenuItem clearToolStripMenuItem1;
    }
}

