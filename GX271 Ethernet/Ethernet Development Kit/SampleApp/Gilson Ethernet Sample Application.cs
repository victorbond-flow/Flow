using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using GilsonEthernet;

namespace Gilson.EthernetSample
{
    public partial class SampleApplication : Form
    {
        private AutoResetEvent connectedEvent = new AutoResetEvent(false);
        private BindingSource bindingSource;
        private DataTable tblCmdParam;
        private EthernetUDPListener udpListener;
        private GilsonTcpList socketList = new GilsonTcpList();
        private InstrumentDefinition currentInstrument = null;
        private List<ExecutionListItem> executionLst = new List<ExecutionListItem>();
        private int sequenceNumber = 1;
        private int previousSelectedIndex = -1;
        
        /// <summary>
        /// Constructor.
        /// </summary>
        public SampleApplication()
        {
            InitializeComponent();

            // Start the UDP Listener on BeaconPort. Call back method BeaconData 
            //will be called for every incoming beacon found.
            udpListener = new EthernetUDPListener(
                new EthernetDataDelegate(BeaconData), GilsonPorts.BeaconPort);
            
            udpListener.Start();

            // Initilalize the DataGrid for Command Parameters.
            InitDataGrid();

            // Start the Worker thread from the thread pool 
            //to update the device status.
            ThreadPool.QueueUserWorkItem(
                new WaitCallback(ThreadVerifyConnectionStatus));
        }

        /// <summary>
        /// Helper thead to update the connection status of the devices
        /// in the list. Also deletes the devices from the tree view if did not 
        /// receive a becaon from a device in the last 10 seconds.
        /// </summary>
        /// <param name="threadContext"></param>
        public void ThreadVerifyConnectionStatus(object context)
        {
            while (this.Disposing == false)
            {
                //Loop through each of the instruments in the tree
                foreach (TreeNode parentNode in treeInstruments.Nodes)
                {
                    //Get the connection information and update the tree with the current connection status
                    ConnectionInformation connectionInfo = parentNode.Tag as ConnectionInformation;
                    if (connectionInfo != null)
                    {
                        UpdateTreeView(connectionInfo.IP, connectionInfo.Port);
                    }
                }
                connectedEvent.WaitOne(10000);
            }
        }


        /// <summary>
        /// Helper method to initialize the DataGrid for Parameters.
        /// </summary>
        private void InitDataGrid()
        {
            // Create the binding source & DataTable for the DataGridView's data source.
            bindingSource = new BindingSource();
            tblCmdParam = new DataTable("CommandParameters", "GilsonEthernetUtility");

            tblCmdParam.Columns.Add("Name").ReadOnly = true;
            tblCmdParam.Columns.Add("Value");
            tblCmdParam.Columns.Add("Units").ReadOnly = true;
            tblCmdParam.Columns.Add("Notes").ReadOnly = true;
            // Set the binding source to DataTable created above.
            bindingSource.DataSource = tblCmdParam;

            // Set the DataGridViews DataSource to bindingSource.
            dataGridCommandParams.DataSource = bindingSource;
        }

        /// <summary>
        /// Callback method which is called for every incoming beacon by the UDP Listener started in the Constructor.
        /// </summary>
        /// <param name="ethernetData">beacon data object GilsonEther.EthernetReturnBase</param>
        private void BeaconData(EthernetReturnBase ethernetData)
        {
            // If the control is created on a different thread than the calling thread.
            if (InvokeRequired)
            {
                this.BeginInvoke(new MethodInvoker(delegate() { BeaconData(ethernetData); }));
            }
            else
            {
                // Populate Device information from the beacon data.
                EthernetBeaconData beaconData = ethernetData as EthernetBeaconData;
                if (beaconData != null && !string.IsNullOrEmpty(beaconData.IP))
                {
                    // Update Tree view
                    UpdateDeviceToTreeView(beaconData);
                }
            }
        }

        /// <summary>
        /// Helper method to add or update InstrumentDefinition to the tree view. This
        /// adds a new node to the treeview if beacaon is from a new ethernet instrument else
        /// udpdates the existing nodes with the incoming device information in the beacon.
        /// </summary>
        /// <param name="beaconData">Incoming beacondata</param>
        private void UpdateDeviceToTreeView(EthernetBeaconData beaconData)
        {
            // If we have already found this device update the device information.
            TreeNode parentNode = treeInstruments.Nodes[beaconData.IP];
            if (parentNode != null)
            {
                //Loop through each device defined in the beacon
                foreach (InstrumentDefinition incomingDeviceInfo in beaconData)
                {
                    //Skip the system device since we do not show this device in the list
                    if (incomingDeviceInfo.Name.Equals("System"))
                        continue;

                    //Update the information in the tree if the device already exists in the tree. 
                    //If the device does not already exist, add it to the tree
                    TreeNode deviceNode = parentNode.Nodes[incomingDeviceInfo.Name];
                    if (deviceNode != null)
                    {
                        InstrumentDefinition deviceInfo = deviceNode.Tag as InstrumentDefinition;
                        if (deviceInfo != null)
                        {
                            deviceInfo.LastTimeFound = DateTime.Now;
                        }
                        else
                        {
                            deviceNode.Tag = incomingDeviceInfo;
                            deviceNode.Name = incomingDeviceInfo.Name;
                        }
                    }
                    else
                    {
                        //The device did not already exist, so we will add it to the tree
                        AddDeviceNode(incomingDeviceInfo, parentNode);
                    }
                }
            }
            // If we found a new ethernet device.
            else
            {
                //This is a new instrument, add it to the tree
                AddInstrumentsToTreeView(beaconData);
            }
        }

        /// <summary>
        /// Adds new instrument information to tree view.
        /// </summary>
        /// <param name="beaconData">beacon data from which to retreive new device information.</param>
        private void AddInstrumentsToTreeView(EthernetBeaconData beaconData)
        {
            TreeNode parentNode = treeInstruments.Nodes.Add(beaconData.IP);
            parentNode.Name = beaconData.IP;
            parentNode.Tag = new ConnectionInformation(beaconData.IP, -1, null);

            //Loop Through each device in the beacon
            foreach (InstrumentDefinition deviceInfo in beaconData)
            {
                //Skip the system device since we do not show this device
                if (deviceInfo.Name.Equals("System"))
                    continue;

                //Add the device to the tree
                AddDeviceNode(deviceInfo, parentNode);
            }
        }

        /// <summary>
        /// Adds device to the parntNode passed.
        /// </summary>
        /// <param name="deviceInfo">Device information(InstrumentDefinition) to add.</param>
        /// <param name="parentNode">Parent node to add device to.</param>
        private void AddDeviceNode(InstrumentDefinition deviceInfo, TreeNode parentNode)
        {
            //Add the device to the parent node
            TreeNode deviceNode = parentNode.Nodes.Add(deviceInfo.Name);
            deviceNode.Name = deviceInfo.Name;
            deviceNode.Tag = deviceInfo; 
        }

        /// <summary>
        /// Event handler for Connect context menu item for the device list.
        /// </summary>
        /// <param name="sender">Event sender</param>
        /// <param name="e">Arguments for the event</param>
        private void connectToolStripMenuItemClick(object sender, EventArgs e)
        {
            //Make sure the instrument definition is not null and that the instrument is not already in our socket list
            if (currentInstrument != null && socketList[currentInstrument.IP, currentInstrument.Port] == null)
            {
                ConnectToDevice(currentInstrument);
            }
        }

        /// <summary>
        /// Helper method to connect to device provided InstrumentDefinition.
        /// </summary>
        /// <param name="deviceInfo">Device Information to connect to.</param>
        private int ConnectToDevice(InstrumentDefinition instrumentDef)
        {
            int port = -1;
            if (instrumentDef != null)
            {

                // Create instance of EthernetSend helper class which handles 
                // the tcp communication to connect to device.
                EthernetSend ethernetSend = new EthernetSend();

                // Request a port to connect to from the device.
                port = ethernetSend.RequestPort(instrumentDef.IP, this.ToString());
                if (port > 0)
                {
                    GilsonTcp tcpSocket = new GilsonTcp(
                        System.Net.IPAddress.Parse(instrumentDef.IP), port);
                    
                    // Hook-up callbacks to be called when the Socket is connected,
                    //Closed & when there is incoming data.
                    tcpSocket.SocketClosed -= new SocketDelegate(SocketClosed);
                    tcpSocket.SocketClosed += new SocketDelegate(SocketClosed);

                    tcpSocket.SocketConnected -= 
                        new SocketDelegate(SocketConnected);
                    
                    tcpSocket.SocketConnected += 
                        new SocketDelegate(SocketConnected);

                    tcpSocket.AddListener(new EthernetDataDelegate(IncomingData));
                    // Keep the new socket in the collection.
                    socketList.Add(tcpSocket);
                    treeInstrumentsAfterSelect(null, null);
                }
            }
            return port;            
        }

        /// <summary>
        /// delegate method passed to GlisonTCP class to be called when there is incoming data
        /// on the socket.
        /// </summary>
        /// <param name="data">Incoming data.</param>
        private void IncomingData(EthernetReturnBase data)
        {
            // If this form is created on a different 
            // thread than the calling thread.
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new EthernetDataDelegate(
                    IncomingData), new object[] { data });
            }
            else
            {
                //Determine the type of response and handle accordingly
                if (data is EthernetResponseData)
                {
                    ProcessResponse(data as EthernetResponseData);
                }
                else if (data is EthernetStatusData)
                {
                    ProcessStatus(data as EthernetStatusData);
                }
            }
        }
    

        /// <summary>
        /// Helper method to process Status data from Device.
        /// </summary>
        /// <param name="statusData">Status response data from device.</param>
        private void ProcessStatus(EthernetStatusData statusData)
        {
            //Get the tree node for the ip address this status message is associated with
            TreeNode parentNode = treeInstruments.Nodes[statusData.IP];
            if (parentNode != null)
            {
                ConnectionInformation connectionInfo = parentNode.Tag as ConnectionInformation;
                if (connectionInfo != null)
                {
                    connectionInfo.LeaseInformation = statusData.LeaseInformation;
                    
                    //Check if someone has a lease on the current instrument & populate the connection information
                    if (connectionInfo.LeaseInformation.Active == false)
                    {
                        connectionInfo.LeaseInformation = null;
                        connectionInfo.LeaseAcquiredTime = DateTime.MinValue;
                        if(!string.IsNullOrEmpty(connectionInfo.LeaseHolderString))
                        {
                            parentNode.Text = string.Format("Connected[{0}:{1}]:{2}", connectionInfo.IP, connectionInfo.Port, connectionInfo.LeaseHolderString);
                        }
                        else
                        {
                            parentNode.Text = string.Format("Connected[{0}:{1}]", connectionInfo.IP, connectionInfo.Port);
                        }
                        treeInstrumentsAfterSelect(null, null);
                    }
                }
            }
        }

        /// <summary>
        /// Helper method to process Response data from Device.
        /// </summary>
        /// <param name="responseData">Response data from device when a message is sent.</param>
        private void ProcessResponse(EthernetResponseData responseData)
        {
            // Get the tree node associated with the IP address from where
            // response is sent.
            ConnectionInformation connectionInfo = null;
            TreeNode parentNode = treeInstruments.Nodes[responseData.IP];
            if (parentNode != null)
            {
                connectionInfo = parentNode.Tag as ConnectionInformation;
            }

            if (ResponseCodeConverter.ConvertCode(
                responseData.ResponseCode).Equals("Success"))
            {
                switch (responseData.CommandName)
                {
                    case EthernetMessages.CommandAdmin:
                        //Set the connection to have admin rights
                        connectionInfo.IsAdmin = true;
                        parentNode.Text = string.Format("Connected[{0}:{1}]:{2}", 
                            connectionInfo.IP, 
                            connectionInfo.Port, 
                            connectionInfo.LeaseHolderString);
                        break;

                    case EthernetMessages.CommandGetInstructionSet:
                        // Create the instance of class InstructionSetDeviceList 
                        //which represents the collection of instruction 
                        //sets for each device.
                        InstructionSetDeviceList instructionSetList = 
                            new InstructionSetDeviceList();

                        // Call InstrumentSetDeviceList.ReadXML() to 
                        // deserialize instruction set XML and populate the 
                        // properties of InstrumentSetDeviceList class 
                        // object created above.
                        instructionSetList.ReadXml("<Gilson>" + 
                            responseData.EthernetReturnParameterList
                            ["Instruction Set"].ParamValue + "</Gilson>");

                        // Loop through each of the devices and retrieve the 
                        // instruction sets for them
                        foreach (TreeNode deviceNode in parentNode.Nodes)
                        {
                            InstrumentDefinition instrumentDef = 
                                deviceNode.Tag as InstrumentDefinition;

                            if (instrumentDef != null)
                            {
                                instrumentDef.InstructionSet = instructionSetList;
                            }
                        }
                        break;

                    case EthernetMessages.CommandGetFirmwareVersion:
                        //Loop through each of the devices and retrieve the firmware versions for them                    
                        foreach (TreeNode deviceNode in parentNode.Nodes)
                        {
                            InstrumentDefinition instrumentDef = deviceNode.Tag as InstrumentDefinition;
                            if (instrumentDef != null)
                            {
                                instrumentDef.FirmwareVersion = responseData.ResponseValue;
                            }
                        }
                        break;

                    case EthernetMessages.CommandRenewLease:
                        //Reset the lease time
                        if (connectionInfo != null)
                        {
                            connectionInfo.LeaseAcquiredTime = DateTime.Now;
                        }
                        parentNode.Text = string.Format("Connected[{0}:{1}]:{2}", connectionInfo.IP, connectionInfo.Port, connectionInfo.LeaseHolderString);
                        break;

                    case EthernetMessages.CommandDropLease:
                        // Process the response for 'Drop Lease' commands response.
                        connectionInfo.LeaseInformation = null;
                        connectionInfo.LeaseAcquiredTime = DateTime.MinValue;
                        if (!string.IsNullOrEmpty(connectionInfo.LeaseHolderString))
                        {
                            parentNode.Text = string.Format("Connected[{0}:{1}]:{2}", connectionInfo.IP, connectionInfo.Port, connectionInfo.LeaseHolderString);
                        }
                        else
                        {
                            parentNode.Text = string.Format("Connected[{0}:{1}]", connectionInfo.IP, connectionInfo.Port);
                        }
                        break;
                }
            }

            // Add all other response data to response list.
            AddResponseToListView(responseData);

            // Update the tree view in case of any changes.
            this.treeInstrumentsAfterSelect(null, null);
        }

        private void AddResponseToListView(EthernetResponseData responseData)
        {
            if (responseData != null)
            {
                string instrumentName = string.Empty;
                // Remove the command form the ExecutionList.
                foreach (ExecutionListItem item in executionLst)
                {
                    if (item.IP == responseData.IP &&
                        item.Port == responseData.PortNumber &&
                        item.SequenceNumber == responseData.SequenceNumber)
                    {
                        executionLst.Remove(item);
                        break;
                    }
                }

                // Get the instrument name. 
                TreeNode parentNode = treeInstruments.Nodes[responseData.IP];
                if (parentNode != null)
                {
                    TreeNode deviceNode = parentNode.Nodes[string.Format("{0}:{1}", responseData.IP, responseData.PortNumber)];
                    if (deviceNode != null)
                    {
                        InstrumentDefinition instrumetnDef = deviceNode.Tag as InstrumentDefinition;
                        if (instrumetnDef != null)
                        {
                            instrumentName = instrumetnDef.Name;
                        }
                    }
                }

                // Build a string for return values.
                StringBuilder returnValue = new StringBuilder(1024);

                //Check if there are return parameters
                if (responseData.EthernetReturnParameterList.Count > 0)
                {
                    //Retrieve the return parameters and add them to the value to put in the response list
                    foreach (EthernetReturnParameter param in responseData.EthernetReturnParameterList)
                    {
                        returnValue.Append(string.Format("[{0}]", param.ToString()));
                    }
                }
                else
                {
                    returnValue.Append(responseData.ResponseValue);
                }

                //Add the information to the response list
                AddMessage(
                    responseData,
                    responseData.SequenceNumber,
                    responseData.IP,
                    responseData.PortNumber,
                    instrumentName,
                    responseData.CommandName,
                    ResponseCodeConverter.ConvertCode(responseData.ResponseCode),
                    returnValue.ToString());
            }
        }

        /// <summary>
        /// Helper method to add messages to & from instrument to the commands List view.
        /// </summary>
        /// <param name="tagValue">Value to assign to the list item.</param>
        /// <param name="sequenceNumber">Sequence number of the message.</param>
        /// <param name="IPAddress">IP Address of the instruments TCP listener.</param>
        /// <param name="port">Port number of the instruments TCP listener.</param>
        /// <param name="instrumentName">Instrument Name.</param>
        /// <param name="commandName">Command Name.</param>
        /// <param name="response">Response value(Success or error) for the command from the instrument.</param>
        /// <param name="returnValue">Return data from the instrument.</param>
        private void AddMessage(
            object tagValue,
            int sequenceNumber,
            string IPAddress,
            int port,
            string instrumentName,
            string commandName,
            string response,
            string returnValue)
        {
            // Add data to list view.
            ListViewItem lstItem = lstCommands.Items.Add(DateTime.Now.ToString(""));
            lstItem.Tag = tagValue != null ? tagValue : commandName;
            lstItem.Name = string.Format("{0}:{1}:{2}", IPAddress, port, sequenceNumber);

            lstItem.SubItems.Add(sequenceNumber.ToString());
            lstItem.SubItems.Add(IPAddress);
            lstItem.SubItems.Add(instrumentName);
            lstItem.SubItems.Add(commandName);
            lstItem.SubItems.Add(response);
            lstItem.SubItems.Add(returnValue); 
        }
            

        /// <summary>
        /// Helper method to update Commands combo box with the 
        /// command for the Instruction Set of the
        /// selected device in the ListView.
        /// </summary>
        /// <param name="deviceName">Device Serial Number.</param>
        private void UpdateCommandList(InstructionSetDeviceList instructionSet,
            string instructionSetName)
        {
            if (instructionSet != null)
            {
                this.cmbCommands.Items.Clear();
                this.cmbCommands.Text = string.Empty;
                this.tblCmdParam.Clear();

                // Get the instruction set for the user selected device.
                InstructionSetDevice deviceInstructionSet =
                    instructionSet[instructionSetName];

                if (deviceInstructionSet != null)
                {
                    // Populate the commands from the instruction set.
                    foreach (InstructionSetCommand command in
                        deviceInstructionSet.Commands)
                    {
                        this.cmbCommands.Items.Add(command.Name);
                    }
                    cmbCommands.SelectedIndex = 0;
                }
            }
        }

        /// <summary>
        /// Method invoked when the socket is closed.
        /// </summary>
        /// <param name="ipAddress">string 'NO IP'</param>
        /// <param name="port">Remote end points Port number(Ethernet devices Port number in this case).</param>
        private void SocketClosed(string ipAddress, int port)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new SocketDelegate(SocketClosed), new object[] { ipAddress, port });
            }
            else
            {
                connectedEvent.Set();
            }
        }

        /// <summary>
        /// Method invoked when the socket is connected.
        /// </summary>
        /// <param name="ipAddress">Remote end points IP Address(Ethernet devices IP Address in this case)</param>
        /// <param name="port">Remote end points Port number(Ethernet devices Port number in this case).</param>
        private void SocketConnected(string ipAddress, int port)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new SocketDelegate(SocketConnected), new object[] { ipAddress, port });
            }
            else
            {
                //Check if we already have a tree node representing the current ipAddress
                TreeNode parentNode = treeInstruments.Nodes[ipAddress];
                if (parentNode != null)
                {
                    foreach (TreeNode deviceNode in parentNode.Nodes)
                    {
                        InstrumentDefinition instrumentDef = deviceNode.Tag as InstrumentDefinition;
                        if (instrumentDef != null)
                        {
                            instrumentDef.Port = port;
                        }
                    }

                    parentNode.Text = string.Format("Connected[{0}:{1}]", ipAddress, port);
                    ConnectionInformation connectionInfo = parentNode.Tag as ConnectionInformation;
                    if (connectionInfo != null)
                    {
                        connectionInfo.Port = port;
                    }
                }
                connectedEvent.Set();
            }
        }

        /// <summary>
        /// Command handler for 'Get Version As Admin' context menu item for device list.
        /// </summary>
        /// <param name="sender">Context menu item.</param>
        /// <param name="e">Event arguments.</param>
        private void getVersionsAsAdminToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                //Send the command to become and admin
                bool success = SendRequest(
                    socketList[currentInstrument.IP, currentInstrument.Port],
                    EthernetMessages.SetAsAdmin);

                if (success == true)
                {
                    AddMessage(null, 0, currentInstrument.IP, currentInstrument.Port, "System", EthernetMessages.CommandAdmin, string.Empty, string.Empty);
                }
            }
        }
        
        /// <summary>
        /// Helper method to send the requet message synchronosly.
        /// </summary>
        /// <param name="tcpSocket">TCP Socket on which to send the request.</param>
        /// <param name="request">Request message string to send over.</param>
        /// <returns>True is succeeded else false</returns>
        private bool SendRequest(GilsonTcp tcpSocket, string request)
        {
            bool returnValue = false;

            //Make sure we are connected
            if (tcpSocket != null && tcpSocket.IsConnected != false && !string.IsNullOrEmpty(request))
            {
                returnValue = true;
                try
                {
                    // Send the request synchronously.
                    tcpSocket.Send(request);
                }
                catch (Exception)
                {
                    //If something unexpected happened, drop the socket
                    socketList.Remove(tcpSocket);
                    returnValue = false;
                }
            }

            return returnValue;
        }
        
        /// <summary>
        /// Event handler for SelectedIndexChanged for commands combo box.
        /// </summary>
        /// <param name="sender">ComboBox</param>
        /// <param name="e">Event Arguments.</param>
        private void cmbCommandsSelectedIndexChanged(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                //Update parameters for the current command
                this.tblCmdParam.Rows.Clear();
                this.tblCmdParam.Rows.Add(new object[] { "Synchronized", "True", string.Empty });
                foreach (InstructionSetParameter parameter in currentInstrument.InstructionSet[currentInstrument.InstructionSetName].Commands[cmbCommands.Text].Parameters)
                {
                    if (parameter.IsReturnParameter == false)
                    {
                        tblCmdParam.Rows.Add(new object[] { parameter.Name, parameter.DefaultValue, parameter.Units, parameter.Notes });
                    }
                }
            }
        }

        /// <summary>
        /// Event handler for button click on btnAdd.
        /// </summary>
        /// <param name="sender">Button</param>
        /// <param name="e">Event Arguments.</param>
        private void btnAddClick(object sender, EventArgs e)
        {
            EthernetMessage message = CreateEthernetMessage();
            if (message != null)
            {
                TreeNode node = new TreeNode(CreateCommandString(message));
                node.Tag = message;
                node.Checked = false;
                if (message.Commands.Count > 0)
                    node.Checked = message.Commands[0].Selected;
                this.treeExecutionList.Nodes.Add(node);
            }
        }

        /// <summary>
        /// Helper method to create a string from the command to be showin in 
        /// Execution List tree.
        /// </summary>
        /// <param name="message">EthernetMessage containing commands.</param>
        /// <returns>Command in the form of string for display.</returns>
        private string CreateCommandString(EthernetMessage message)
        {
            StringBuilder sb = new StringBuilder(1000);
            EthernetCommand command = message.Commands[0];
            if (command != null)
            {
                sb.Append(command.CommandName + " [" + command.DeviceName + " : " + message.IP + ":" + message.PortNumber.ToString() + "]");
                foreach (EthernetParameter param in command.Parameters)
                {
                    sb.Append(" " + param.Name + "=" + param.Value);
                }
            }
            return sb.ToString();
        }


        /// <summary>
        /// Creates the EthernetMessage from the command selected.
        /// </summary>
        /// <returns>EthernetMessage formed from the command.</returns>
        private EthernetMessage CreateEthernetMessage()
        {
            EthernetMessage ethernetMsg = null;

            if (currentInstrument != null && socketList[
                currentInstrument.IP, currentInstrument.Port] != null)
            {
                // Create the EthernetMessage into which commands 
                // will be inserterd. EthernetMessage represents the 
                // XML message sent to the ethernet instrument. Assign 
                // the ethernet instruments IP Address and Port information.
                ethernetMsg = new EthernetMessage();
                ethernetMsg.IP = currentInstrument.IP;
                ethernetMsg.PortNumber = currentInstrument.Port;

                // Create the EthernetCommand object with Command Name, 
                // Instruction Set Name(Device Name), GSIOC ID of the 
                // Ethernet instrument, synchronized is set to false.
                EthernetCommand command = new EthernetCommand(
                    cmbCommands.Text,
                    currentInstrument.InstructionSetName,
                    currentInstrument.UnitID,
                    false);

                command.Selected = true;

                // Populate the command with the command parameters. 
                // Command parameter is represented by EthernetParameter class.
                foreach (DataRow dataRow in tblCmdParam.Rows)
                {
                    if (dataRow[0].ToString().Equals("Synchronized"))
                    {
                        command.Synchronize = 
                            dataRow[1].ToString().ToLower().Equals("true");
                    }
                    else
                    {
                        command.Parameters.Add(new EthernetParameter(
                            dataRow[0].ToString(), dataRow[1].ToString()));
                    }
                }

                // Add the command object EthernetCommand created above to 
                // message object EthernetMessage.
                ethernetMsg.Commands.Add(command);
            }

            return ethernetMsg;
        }

        /// <summary>
        /// Private helper method to update SequenceNumber for the commands to be 
        /// sent to the instrument.
        /// </summary>
        private void UpdateSequenceNumbers()
        {
            // if the Sequence number is close to int.MaxValue reset to 1.
            if (sequenceNumber > int.MaxValue - 10)
            {
                sequenceNumber = 1;
            }
            
            // Go through the list of commands to be executed and update the sequence
            // number sequentially.
            foreach (TreeNode node in this.treeExecutionList.Nodes)
            {
                EthernetMessage message = node.Tag as EthernetMessage;
                if (message != null)
                {
                    foreach (EthernetCommand command in message.Commands)
                    {
                        command.SequenceNumber = ++sequenceNumber;
                    }
                }
            }
        }

        /// <summary>
        /// Private helpe method to send EthernetMessage to the instrument.
        /// </summary>
        /// <param name="message">Message represented by EthernetMessage to be sent to instrument.</param>
        private void SendMessage(EthernetMessage message)
        {
            GilsonTcp tcpSocket = null;
            if (currentInstrument != null && 
                socketList[currentInstrument.IP, currentInstrument.Port] != null)
            {
                try
                {
                    // Get the socket connected to the IP:Port from the socket 
                    // list to which this message has to be sent.
                    tcpSocket = socketList[message.IP, message.PortNumber];
                    if (tcpSocket != null)
                    {
                        tcpSocket.TcpSend(message);
                    }

                    // Add all the command to the list.
                    foreach (EthernetCommand cmd in message.Commands)
                    {
                        executionLst.Add(new ExecutionListItem(message.IP, message.PortNumber, cmd.UnitID, cmd.SequenceNumber));
                        AddMessage(cmd, cmd.SequenceNumber, message.IP, message.PortNumber, currentInstrument.Name, cmd.CommandName, "", "NA");
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show(ex.Message, "Send Message Failed");
                    DisposeSocket(tcpSocket);
                }
            }
        }

        /// <summary>
        /// Helper method to add sent command to the list view.
        /// </summary>
        /// <param name="ip">IP Address to which command is sent.</param>
        /// <param name="port">Port number to which command is sent.</param>
        /// <param name="command">Comamnd.</param>
        private void AddToCommandsListView(string ip, int port, EthernetCommand command)
        {
            if (command != null)
            {
                ListViewItem lstItem = lstCommands.Items.Add(DateTime.Now.ToString());
                lstItem.Tag = command;
                lstItem.Name = string.Format("{0}:{1}:{2}", ip, port, command.SequenceNumber);

                lstItem.SubItems[clmSeq.Index].Text = command.SequenceNumber.ToString();
                lstItem.SubItems[clmID.Index].Text = ip;
                lstItem.SubItems[clmInstrument.Index].Text = command.DeviceName;
                lstItem.SubItems[clmCommand.Index].Text = command.CommandName;
                lstItem.SubItems[clmReturnValues.Index].Text = "NA";
            }
        }

        /// <summary>
        /// Private helper method to dispose the socket.
        /// </summary>
        /// <param name="socket">socket to dispose.</param>
        private void DisposeSocket(GilsonTcp socket)
        {
            if (socket != null)
            {
                // Dispose the socket if connected.
                if (socket.IsConnected)
                {
                    string ipAddress = socket.IPAddress;
                    int port = socket.Port;

                    // Disconnect the socket.
                    socket.Disconnect();

                    // Remove from the socket list.
                    if (socketList.Contains(socket))
                        socketList.Remove(socket);

                    // Clean up other things associated with the connecting represented by socket.
                    SocketClosed(ipAddress, port);
                }
            }
        }

        /// <summary>
        /// Event handler for ExecutionList context menu item 'Execute'.
        /// </summary>
        /// <param name="sender">Context menu item.</param>
        /// <param name="e">Event arguments</param>
        private void executeToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (this.treeExecutionList.SelectedNode != null)
            {
                EthernetMessage message = treeExecutionList.SelectedNode.Tag as EthernetMessage;
                if (message != null)
                {
                    SendMessage(message);
                }
            }
        }

        /// <summary>
        /// Event handler for ExecutionList context menu item 'Delete'.
        /// </summary>
        /// <param name="sender">Context menu item.</param>
        /// <param name="e">Event arguments.</param>
        private void deleteToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (treeExecutionList.SelectedNode != null)
            {
                treeExecutionList.Nodes.Remove(treeExecutionList.SelectedNode);
            }
        }

        /// <summary>
        /// Event handler for ExecutionList context menu item 'Update Sequence Numbers'
        /// </summary>
        /// <param name="sender">Context menu item</param>
        /// <param name="e">Event arguments.</param>
        private void updateSequenceToolStripMenuItemClick(object sender, EventArgs e)
        {
            UpdateSequenceNumbers();
        }

        /// <summary>
        /// Event handler for DeviceList context menu item 'Disconnect'.
        /// </summary>
        /// <param name="sender">Context menu item.</param>
        /// <param name="e">Event arguments.</param>
        private void disconnectToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (currentInstrument != null && socketList[currentInstrument.IP, currentInstrument.Port] != null)
            {
                GilsonTcp tcpSocket = socketList[currentInstrument.IP, currentInstrument.Port];
                if (tcpSocket != null)
                {
                    DisposeSocket(tcpSocket);
                }
            }
        }

        /// <summary>
        /// Event handler for treeInstruments.AfterSelect.
        /// </summary>
        /// <param name="sender">treeInstruments</param>
        /// <param name="e">Event arguments</param>
        private void treeInstrumentsAfterSelect(object sender, TreeViewEventArgs e)
        {
            // If selected TreeNOde is the IP Address node.
            //
            if (treeInstruments.SelectedNode == null || treeInstruments.SelectedNode.Level == 0)
            {
                currentInstrument = null;
            }
            else
            {

                // Get the selected Device and the associated IP Address node.
                TreeNode deviceNode = treeInstruments.SelectedNode;
                TreeNode parentNode = deviceNode.Parent;

                // Get the InstrumentDefinition associated to the device node whille processing
                // beacon data above in BeaconData(). Set the currentInstrument member to the
                // Instrumet
                currentInstrument = deviceNode.Tag as InstrumentDefinition;
                if (currentInstrument != null)
                {
                    // Get the ConnectionInformation class object associated with the IP Address Node.
                    ConnectionInformation connectionInfo = parentNode.Tag as ConnectionInformation;
                    LeaseInfo leaseInfo = connectionInfo.LeaseInformation;


                    // Populate the list displaying the device information.
                    lstInstrumentProps.Items[0].SubItems[clmPropertyValue.Index].Text = currentInstrument.IP;
                    lstInstrumentProps.Items[1].SubItems[clmPropertyValue.Index].Text = currentInstrument.Port.ToString();
                    lstInstrumentProps.Items[2].SubItems[clmPropertyValue.Index].Text = currentInstrument.UnitID.ToString();
                    lstInstrumentProps.Items[3].SubItems[clmPropertyValue.Index].Text = currentInstrument.SerialNumber;

                    // Add Instructionset Version, Instructionset Name & System Version.
                    string instructionSetVersion = "";
                    string systemVersion = "";
                    if (currentInstrument.InstructionSet != null)
                    {
                        instructionSetVersion = currentInstrument.InstructionSet[currentInstrument.InstructionSetName].Version;
                        systemVersion = currentInstrument.InstructionSet["System"].Version;
                    }

                    lstInstrumentProps.Items[4].SubItems[clmPropertyValue.Index].Text = instructionSetVersion;
                    lstInstrumentProps.Items[5].SubItems[clmPropertyValue.Index].Text = currentInstrument.InstructionSetName;
                    lstInstrumentProps.Items[6].SubItems[clmPropertyValue.Index].Text = systemVersion;
                    lstInstrumentProps.Items[7].SubItems[clmPropertyValue.Index].Text = "";
                    lstInstrumentProps.Items[8].SubItems[clmPropertyValue.Index].Text = currentInstrument.FirmwareVersion;
                    lstInstrumentProps.Items[9].SubItems[clmPropertyValue.Index].Text = currentInstrument.Group;
                    lstInstrumentProps.Items[10].SubItems[clmPropertyValue.Index].Text = leaseInfo != null ? connectionInfo.LeaseAcquiredTime.ToString("hh:mm:ss") : "NA";
                    lstInstrumentProps.Items[11].SubItems[clmPropertyValue.Index].Text = leaseInfo != null ? leaseInfo.LeaseTimeRemaining.TotalSeconds.ToString() : "NA";

                    // If the device selected by user in the TreeView changes, update the command list combo box with the commands
                    // for the device selected from the instruction set obtained by sending 'Get Instruction Set' command(see ProcessResponse() method).
                    if (previousSelectedIndex != treeInstruments.SelectedNode.Index && currentInstrument.InstructionSet != null)
                    {
                        // Populate commands form the Device seleted.
                        //
                        UpdateCommandList(currentInstrument.InstructionSet, currentInstrument.InstructionSetName);

                        // Store the selected device TreeNode index.
                        //
                        previousSelectedIndex = treeInstruments.SelectedNode.Index;
                    }
                }
            }
        }

        /// <summary>
        /// Event handler for DeviceList context menu item 'Get Instruction Set'.
        /// </summary>
        /// <param name="sender">Context menu item.</param>
        /// <param name="e">Event arguments.</param>
        private void toolStripMenuItemGetInstructionSetClick(object sender, EventArgs e)
        {
            // If the current selection is not null or the socket connection to the device selection is active.
            if (currentInstrument != null)
            {
                bool success = SendRequest(
                    socketList[currentInstrument.IP, 
                    currentInstrument.Port],
                    EthernetMessages.GetInstructionSet);
                if (success == true)
                {
                    AddMessage(null, 0, currentInstrument.IP, currentInstrument.Port, "System", EthernetMessages.CommandGetInstructionSet, string.Empty, string.Empty);
                }
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void getFirmwareVersionToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                bool success = SendRequest(
                    socketList[currentInstrument.IP, currentInstrument.Port],
                    EthernetMessages.GetFirmwareVersion);
                if (success == true)
                {
                    AddMessage(null, 0, currentInstrument.IP, currentInstrument.Port, "System", EthernetMessages.CommandGetFirmwareVersion, string.Empty, string.Empty);
                }
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void renewLeaseToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                bool success = SendRequest(
                    socketList[currentInstrument.IP, currentInstrument.Port],
                    EthernetMessages.RenewLease);
                if (success)
                {
                    AddMessage(null, 0, currentInstrument.IP, currentInstrument.Port, "System", EthernetMessages.CommandRenewLease, string.Empty, string.Empty);
                }
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void dropLeaseToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                bool success = SendRequest(
                    socketList[currentInstrument.IP, currentInstrument.Port],
                    EthernetMessages.DropLease);
                if (success == true)
                {
                    AddMessage(null, 0, currentInstrument.IP, currentInstrument.Port, "System", EthernetMessages.CommandDropLease, string.Empty, string.Empty);
                }
            }
        }

        /// <summary>
        /// Event handler for btnExecute click event.
        /// </summary>
        /// <param name="sender">btnExecute.</param>
        /// <param name="e">Event arguments.</param>
        private void btnExecuteClick(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                //Get the socket for the current instrument
                GilsonTcp tcpSocket = socketList[currentInstrument.IP, currentInstrument.Port];
                if (tcpSocket == null || tcpSocket.IsConnected == false)
                {
                    MessageBox.Show("Please connect to device to execute.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
                else
                {
                    UpdateSequenceNumbers();

                    foreach (TreeNode node in this.treeExecutionList.Nodes)
                    {
                        EthernetMessage msg = node.Tag as EthernetMessage;
                        if (msg != null)
                        {
                            //Send the Ethernet message to the instrument
                            SendMessage(msg);
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Event handler for command list view context menu command getLastResponseToolStripMenuItem.
        /// </summary>
        /// <param name="sender">Command list view context menu.</param>
        /// <param name="e">Event arguments.</param>
        private void getLastResponseToolStripMenuItemClick(object sender, EventArgs e)
        {
            if (currentInstrument != null)
            {
                bool success = SendRequest(
                    socketList[currentInstrument.IP, currentInstrument.Port],
                    EthernetMessages.GetLastResponse);
                if (success == true)
                {
                    AddMessage(null, 0, currentInstrument.IP, currentInstrument.Port, "System", EthernetMessages.CommandGetLastResponse, string.Empty, string.Empty);
                }
            }
        }

        /// <summary>
        /// Helper method to update tree view based on the beacon received time
        /// from the ethernet instrument.
        /// </summary>
        /// <param name="IPAddress">IP Address of the ethernet instrumnet</param>
        private void UpdateTreeView(string IPAddress, int port)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new MethodInvoker(delegate() { UpdateTreeView(IPAddress, port); }));
            }
            else
            {
                CheckForLastBeaconTimeFrom(IPAddress, port);
            }
        }

        /// <summary>
        /// Checks the last arrival time of the beacon from the instrument at the
        /// specified IP Address & Port. If last beacon received time is more than 10 seconds 
        /// it is assumed that the device is not connected and removes the device from the tree view.
        /// </summary>
        /// <param name="IPAddress">IP Address of the ethernet instrument.</param>
        private void CheckForLastBeaconTimeFrom(string IPAddress, int port)
        {
            if (!string.IsNullOrEmpty(IPAddress))
            {
                // Verify last time we received a becaon from the ethernet 
                // instrument with the passed IP Address. If the device did
                // not send a beacon for over 10 seconds we assume that the
                // device is no longer on the ethernet and remove it from
                // the tree view.
                TreeNode parentNode = treeInstruments.Nodes[IPAddress];
                if (parentNode != null)
                {
                    ConnectionInformation connectionInfo = parentNode.Tag as ConnectionInformation;
                    foreach (TreeNode deviceNode in parentNode.Nodes)
                    {
                        InstrumentDefinition instrumentDef = deviceNode.Tag as InstrumentDefinition;
                        if (instrumentDef != null)
                        {
                            if ((DateTime.Now - instrumentDef.LastTimeFound).TotalSeconds > 10)
                            {
                                parentNode.Nodes.Remove(deviceNode);
                            }
                        }
                    }

                    // If no devices exist under the IP Address
                    if (parentNode.Nodes.Count <= 0)
                    {
                        treeInstruments.Nodes.Clear();
                        foreach (ListViewItem item in lstInstrumentProps.Items)
                        {
                            item.SubItems[1].Text = string.Empty;
                        }
                        this.cmbCommands.Items.Clear();
                        this.lstCommands.Items.Clear();
                    }
                    else
                    {
                        // Update the connection status for the tree node with the IP Address.
                        GilsonTcp tcpSocket = socketList[IPAddress, port];
                        if (tcpSocket == null || tcpSocket.IsConnected == false)
                        {
                            // If we are not connected to the instrument, initialize the LeaseInformation, 
                            // port & version information.
                            connectionInfo.LeaseInformation = null;
                            connectionInfo.IsAdmin = false;
                            connectionInfo.LeaseAcquiredTime = DateTime.MinValue;
                            connectionInfo.Port = -1;

                            foreach (TreeNode deviceNode in parentNode.Nodes)
                            {
                                InstrumentDefinition instrumentDef = deviceNode.Tag as InstrumentDefinition;
                                if (instrumentDef != null)
                                {
                                    instrumentDef.Port = -1;
                                    instrumentDef.PromVersion = string.Empty;
                                    instrumentDef.FirmwareVersion = string.Empty;
                                }
                            }

                            // If we are not connection change the text on the IP Address node to
                            // just IP Address.
                            parentNode.Text = IPAddress;
                            treeInstrumentsAfterSelect(null, null);
                        }
                        treeInstruments.Update();
                    }
                }
            }
        }

        /// <summary>
        /// Event handler for ctxDeviceCommunication Opening event.
        /// </summary>
        /// <param name="sender">ctxDeviceCommunication.</param>
        /// <param name="e">Event arguments.</param>
        private void ctxDevcieCommunicationOpening(object sender, CancelEventArgs e)
        {
            // If this method is called from a different thread than the one in which
            // this form is created, call this method on the thread in which this form
            // is created.
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new MethodInvoker(delegate() { ctxDevcieCommunicationOpening(sender, e); }));
            }
            else
            {
                // If the selection in the tree view is not a device node or there is no selection 
                // do not show the context menu.
                if (currentInstrument == null && treeInstruments.SelectedNode != null)
                {
                    e.Cancel = true;
                }
                else
                {
                    // Get the tree node with IP Address
                    TreeNode parentNode = treeInstruments.SelectedNode.Level == 0 ? treeInstruments.SelectedNode : treeInstruments.SelectedNode.Parent;
                    if (parentNode != null)
                    {

                        // Get the helper class ConnectionInformation associated with the IP Address node.
                        ConnectionInformation connectionInfo = parentNode.Tag as ConnectionInformation;
                        if (connectionInfo != null)
                        {

                            // Get the TCP Socket associated with IP Address & Port.
                            GilsonTcp tcpSocket = socketList[connectionInfo.IP, connectionInfo.Port];

                            // Check to see if the connection is active and update the context menu commands
                            // Enabled state based on the connection status.
                            bool connected = (tcpSocket != null && tcpSocket.IsConnected);
                            {
                                this.connectToolStripMenuItem.Enabled = !connected;
                                this.getFirmwareVersionToolStripMenuItem.Enabled = connected;
                                this.systemToolStripMenuItem.Enabled = connected;
                                this.setAsAdminToolStripMenuItem.Enabled = connected;
                                this.toolStripMenuItemGetInstructionSet.Enabled = connected;
                                this.disconnectToolStripMenuItem.Enabled = connected;

                                bool leaseActive = (connected && connectionInfo.LeaseInformation != null && connectionInfo.LeaseInformation.Active);
                                this.renewLeaseToolStripMenuItem.Enabled = !leaseActive;
                                this.dropLeaseToolStripMenuItem.Enabled = leaseActive;
                            }
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Method called when the from is closed by the user.
        /// </summary>
        /// <param name="sender">Form</param>
        /// <param name="e">Event arguments.</param>
        private void frmMainFormClosing(object sender, FormClosingEventArgs e)
        {
            // Stop the Beacon listener.
            if (udpListener != null)
            {
                this.udpListener.Stop();
                this.udpListener = null;
            }

            // Disconnect all the socket connections.
            foreach(GilsonTcp tcpSocket in socketList)
            {
                if(tcpSocket.IsConnected || tcpSocket.IsConnecting)
                {
                    tcpSocket.Disconnect();
                }
            }

            socketList.Clear();
            socketList = null;
        }

        /// <summary>
        /// Event handler for btnDelete. Removes selected items from the execution list.
        /// </summary>
        /// <param name="sender">Button item.</param>
        /// <param name="e">Event arguments.</param>
        private void btnDeleteClick(object sender, EventArgs e)
        {
            foreach(TreeNode node in treeExecutionList.Nodes)
            {
                if(node.IsSelected)
                {
                    treeExecutionList.Nodes.Remove(node);
                }
            }
        }

        /// <summary>
        /// Event handler for ExecutionList context menu item 'Clear'.
        /// </summary>
        /// <param name="sender">Context menu item.</param>
        /// <param name="e">Event arguments.</param>
        private void clearToolStripMenuItemClick(object sender, EventArgs e)
        {
            treeExecutionList.Nodes.Clear();
        }

        private void clearToolStripMenuItem1Click(object sender, EventArgs e)
        {
            this.lstCommands.Items.Clear();
        }

        /// <summary>
        /// Internal class used for holding onto connection information
        /// </summary>
        internal class ConnectionInformation
        {
            public ConnectionInformation(
                        string ipAddress,
                        int port,
                        LeaseInfo leaseInfo)
            {
                LeaseInformation = leaseInfo;
                IP = ipAddress;
                Port = port;
                LeaseAcquiredTime = DateTime.MinValue;
                IsAdmin = false;
            }

            /// <summary>
            /// Get/Set LeaseInformation.
            /// </summary>
            public LeaseInfo LeaseInformation
            {
                get;
                set;
            }

            /// <summary>
            /// Get/Set ethernet devices Port number.
            /// </summary>
            public int Port
            {
                get;
                set;
            }

            /// <summary>
            /// Get/Set ethernet devices IP Address.
            /// </summary>
            public string IP
            {
                get;
                set;
            }

            /// <summary>
            /// Get/Set DateTime when the lease is acquired with the 
            /// ethernet instrument.
            /// </summary>
            public DateTime LeaseAcquiredTime
            {
                get;
                set;
            }

            public string LeaseHolderString
            {
                get
                {
                    if (IsAdmin && LeaseAcquiredTime == DateTime.MinValue)
                        return "Admin";
                    else if (IsAdmin && LeaseAcquiredTime != DateTime.MinValue)
                        return "Admin & Lease Holder";
                    else if (!IsAdmin && LeaseAcquiredTime != DateTime.MinValue)
                        return "Lease Holder";

                    return string.Empty;
                }
            }

            /// <summary>
            /// Get/Set if Admin privilage is acquired.
            /// </summary>
            public bool IsAdmin
            {
                get;
                set;
            }
        }
    }
}
