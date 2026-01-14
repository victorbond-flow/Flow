using System;
using System.Drawing;
using System.Collections;
using System.Collections.Generic;
using System.Configuration;
using System.Management;
using System.Net.NetworkInformation;
using System.Windows.Forms;
using System.Text.RegularExpressions;
using System.Threading;
using GilsonEthernet;

namespace Verity4000SeriesExampleGEARS
{
    /// <summary>
    /// Summary description for Form1.
    /// </summary>
    public class Example : System.Windows.Forms.Form
    {
		#region Private Static Members

        static private string APP_TITLE_PRODUCTION = "Example";
        static private string APP_TITLE_SERVICE = "Example";
		static private string[] commandLineArgs;

		#endregion

		#region ENUM Members

		private enum APP_MODE { production, service };
        private enum LEDControls { Unknown, BeaconStatus, Connected, Home, ValveLED, RightSyringeLED, LeftSyringeLED, RightSensorLED, LeftSensorLED, SerialNumber, 
									LeftValveR, LeftValveN, LeftValveG, RightValveR, RightValveN, RightValveG, SingleModuleLED, LeftModuleLED, RightModuleLED };
        private enum TextControls { Unknown, CurrentSerialNumber, ErrorState, LeftSensorPressure, RightSensorPressure, LeftHeldVolume, RightHeldVolume};
        private enum LabelControls { Unknown, Connect, LeftPressureUnits, RightPressureUnits, ConnectedInstrumentName, ConnectedInstrumentFWVersion, ProgramUSBWarning};
        private enum ButtonControls { Unknown, Home, Reset, SetSerialNumber, LeftSyringeTest, RightSyringeTest, ValveTest, ZeroLeftSensor, ZeroRightSensor, LeftButton, RightButton};

		#endregion

		#region Private Members

        private Hashtable hashFlowRates = new Hashtable();
        private APP_MODE app_mode = APP_MODE.production;
        private ArrayList executionList = new ArrayList();
		private ArrayList _MACAddresses	= new ArrayList();
		private int sequenceNumber		= 0;

		private object SendLock = new object();
        private bool connectedOnLastBeacon = false;
		private bool _ZeroLeft	= true;
		private bool _ZeroRight	= true;


		private ArrayList instrumentsToLookFor	= new ArrayList();
		private SortedList modelTypesToLookFor	= new SortedList();
		private SortedList syringeTypesToLookFor= new SortedList();
		private const string defaultFWVersion	= "x.x.x.x";
		private string currentInstrumentName	= String.Empty;
		private string currentFirmwareVersion	= defaultFWVersion;
		private string leftInstrumentName		= String.Empty;
		private string rightInstrumentName		= String.Empty;
		private string serialNumberFormat		= "64...J...";
		private string serialNumberFormatLabel	= "_ _ _ _ _ _ _ _ _";
		private bool pressureSensorAvailable	= false;
		private bool CheckedUnitID	= false;

		#region Ethernet Stuff

		private int beaconSearchTimeout = 6000;//15000;
        private System.Timers.Timer beaconTimer = new System.Timers.Timer();
        private System.Timers.Timer statusTimer = new System.Timers.Timer();
        private bool beaconImageState;
        private int beaconLEDcountdown = 1;
        private EthernetUDPListener beaconListener;
        private GilsonTcpList socketList = new GilsonTcpList();
        private GilsonTcp currentGTCP = null;
        private EthernetResponseData responseData = new EthernetResponseData();
        private EthernetStatusData statusData = new EthernetStatusData();
        private InstrumentDefinitionList instrumentList = new InstrumentDefinitionList();
        private InstrumentDefinition connectedInstrument = new InstrumentDefinition();

		#endregion

        private delegate void SetLEDImageDelegate(LEDControls pb, Image image);
        private delegate void SetLabelTextDelegate(LabelControls label, string text);
        private delegate void ShowLabelTextDelegate(LabelControls label, bool text);
        private delegate string GetTextBoxTextDelegate(TextControls textBox);
        private delegate void SetTextBoxTextDelegate(TextControls textBox, string text);
        private delegate void SetButtonEnabledStateDelegate(ButtonControls button, bool state);
        private delegate void ResetLEDsAndButtonsDelegate();
        private delegate void clickConnectDelegate();
        private delegate void VoidNoArgsDelegate();
        private delegate bool BoolNoArgsDelegate();
        private string rightUnitID = string.Empty;
        private string leftUnitID = string.Empty;
        private string rightSyringeSize = string.Empty;
        private string leftSyringeSize = string.Empty;
        private string rightSyringeRate = string.Empty;
        private string leftSyringeRate = string.Empty;
        private string rightPressureReading = string.Empty;
        private string leftPressureReading	= string.Empty;
        private string rightPressureOffset	= string.Empty;
        private string leftPressureOffset	= string.Empty;
        private string rightValvePosition	= string.Empty;
        private string leftValvePosition	= string.Empty;
        private string rightVolumne			= string.Empty;
        private string leftVolumne			= string.Empty;
        private long standardTimeout = 3000L;
        private string devicePreviousErrorCode = string.Empty;
        private bool newStatus			= false;
        private bool rightSyringeMotor	= false;
        private bool leftSyringeMotor	= false;
        private bool rightValveMotor	= false;
        private bool leftValveMotor		= false;
		private int leftValveType		= 3;
		private int rightValveType		= 3;

		#endregion

		#region Strings

		private enum Message
		{
			Error_communicating_with_left_syringe,
			Error_aspirating_from_left_syringe,
			Error_dispensing_from_left_syringe,
			Error_communicating_with_right_syringe,
			Error_aspirating_with_right_syringe,
			Error_dispensing_with_right_syringe
		};

		private string[] OriginalMessages	= {
										"Error communicating with left syringe.",
										"Error aspirating from left syringe.",
										"Error dispensing from left syringe.",
										"Error communicating with right syringe.",
										"Error aspirating with right syringe.",
										"Error dispensing with right syringe."
										};

		private string[] Messages	= {
										"Error communicating with left syringe.",
										"Error aspirating from left syringe.",
										"Error dispensing from left syringe.",
										"Error communicating with right syringe.",
										"Error aspirating with right syringe.",
										"Error dispensing with right syringe."
										};

		#endregion

        private System.Windows.Forms.Button buttValveTest;
        private System.Windows.Forms.Button buttZeroLeftSensor;
        private System.Windows.Forms.Button buttZeroRightSensor;
        private System.Windows.Forms.TextBox tbLeftSensorPressure;
		private System.Windows.Forms.TextBox tbRightSensorPressure;
        private System.Windows.Forms.Label bar;
        private System.Windows.Forms.Label label2;
		private System.ComponentModel.IContainer components;
        private System.Windows.Forms.ImageList ilLEDs;
        private System.Windows.Forms.PictureBox pbValveLED;
		private System.Windows.Forms.PictureBox pbRightSensorLED;
        private System.Windows.Forms.PictureBox pbConnected;
        private System.Windows.Forms.PictureBox pbLeftSensorLED;
        private System.Windows.Forms.PictureBox pbBeaconStatus;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.PictureBox pbLFV_R;
        private System.Windows.Forms.PictureBox pbLFV_N;
        private System.Windows.Forms.PictureBox pbLFV_G;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.Label label6;
        private System.Windows.Forms.Label label7;
        private System.Windows.Forms.Label label8;
        private System.Windows.Forms.Label label9;
        private System.Windows.Forms.Label label10;
        private System.Windows.Forms.PictureBox pbRFV_G;
        private System.Windows.Forms.PictureBox pbRFV_N;
        private System.Windows.Forms.PictureBox pbRFV_R;
        private System.Windows.Forms.Label label11;
        private System.Windows.Forms.Label label12;
        private System.Windows.Forms.TextBox tbLeftHeldVolume;
        private System.Windows.Forms.TextBox tbRightHeldVolume;
        private System.Windows.Forms.Label label13;
        private System.Windows.Forms.Label label14;
        private System.Windows.Forms.Button buttHome;
		private System.Windows.Forms.PictureBox pbHome;
        private System.Windows.Forms.TextBox tbCurrentSerialNumber;
        private System.Windows.Forms.Label label16;
        private System.Windows.Forms.Label label17;
        private System.Windows.Forms.Label label18;
        private System.Windows.Forms.Button buttLeftSyringeTest;
        private System.Windows.Forms.Button buttRightSyringeTest;
        private System.Windows.Forms.PictureBox pbLeftSyringeLED;
        private System.Windows.Forms.PictureBox pbRightSyringeLED;
        private System.Windows.Forms.Button AboutButton;
        private System.Windows.Forms.Label ConnectStatlbl;
        private System.Windows.Forms.Label VersionInfo;
        private TextBox textBoxErrorState;
		private Label label19;
		private Label ConnectedInstrumentName;
		private PictureBox RightValvePictureBox;
		private PictureBox MachinePictureBox;
		private PictureBox LeftModuleLED;
		private PictureBox RightModuleLED;
		private PictureBox SingleModuleLED;
		private ImageList DeviceImageList;
		private PictureBox LeftValvePictureBox;
		private PictureBox LargeMachinePictureBox;
		private ImageList PumpImageList;
		private Panel TestPanel;
		private Panel panel1;
		private Label label15;
		private Label ProgramQuestionLabel;
		private Label PowerQuestionLabel;

		#region Constructor

		/// <summary>
		/// Example constructor.
		/// Initialize GUI and start timers.
		/// </summary>
        public Example()
        {
            //
            // Required for Windows Designer support
            //
            InitializeComponent();

			if (ConfigurationManager.AppSettings["APP_TITLE_PRODUCTION"] != null)
			{
				APP_TITLE_PRODUCTION	= ConfigurationManager.AppSettings["APP_TITLE_PRODUCTION"];
			}
			if (ConfigurationManager.AppSettings["APP_TITLE_SERVICE"] != null)
			{
				APP_TITLE_SERVICE	= ConfigurationManager.AppSettings["APP_TITLE_SERVICE"];
			}
			if (ConfigurationManager.AppSettings["Serial Number Format"] != null)
			{
				serialNumberFormat	= ConfigurationManager.AppSettings["Serial Number Format"];
			}
			if (ConfigurationManager.AppSettings["Serial Number Format Label"] != null)
			{
				serialNumberFormatLabel	= ConfigurationManager.AppSettings["Serial Number Format Label"];
			}
			for (int ii = 1; ii < 100; ii++)
			{
				if (ConfigurationManager.AppSettings["Instrument " + ii] != null)
				{
					instrumentsToLookFor.Add(ConfigurationManager.AppSettings["Instrument " + ii]);
				}
			}
			for (int ii = 1; ii < 100; ii++)
			{
				if (ConfigurationManager.AppSettings["Model Type " + ii] != null)
				{
					if (ConfigurationManager.AppSettings["Model Type " + ConfigurationManager.AppSettings["Model Type " + ii]] != null)
					{
						if (!modelTypesToLookFor.Contains(ConfigurationManager.AppSettings["Model Type " + ii]))
						{
							modelTypesToLookFor.Add(ConfigurationManager.AppSettings["Model Type " + ii], ConfigurationManager.AppSettings["Model Type " + ConfigurationManager.AppSettings["Model Type " + ii]]);
						}
						if (!syringeTypesToLookFor.Contains(ConfigurationManager.AppSettings["Model Type " + ii]))
						{
							if (ConfigurationManager.AppSettings["Syringe Type " + ConfigurationManager.AppSettings["Model Type " + ii]] != null)
							{
								syringeTypesToLookFor.Add(ConfigurationManager.AppSettings["Model Type " + ii], ConfigurationManager.AppSettings["Syringe Type " + ConfigurationManager.AppSettings["Model Type " + ii]]);
							}
						}
					}
				}
			}
            this.StartPosition = FormStartPosition.CenterScreen;
            resetLEDsAndButtons();
            setLEDImages(LEDControls.BeaconStatus, ilLEDs.Images[5]);
            beaconImageState = false;
            ConnectStatlbl.Text = "No Device Found";
            VersionInfo.Text = "Firmware Version: " + "x.x.x.x";	//Application.ProductVersion;
            beaconListener = new EthernetUDPListener(new EthernetDataDelegate(ethernetBeaconData), GilsonPorts.BeaconPort);
            beaconListener.Start();

            //populate hashtable that holds syringe size/flow rate pairs
            hashFlowRates.Add("100", "4");
            hashFlowRates.Add("250", "10");
            hashFlowRates.Add("500", "20");
            hashFlowRates.Add("1000", "40");
            hashFlowRates.Add("5000", "100");
            hashFlowRates.Add("10000", "100");
            hashFlowRates.Add("25000", "100");

			// timer used to keep track of beacon presence
			beaconTimer.Interval = beaconSearchTimeout;
			beaconTimer.Elapsed += new System.Timers.ElapsedEventHandler(beaconTimer_Elapsed);
			beaconTimer.AutoReset = true;
			beaconTimer.Start();

			statusTimer.Interval = beaconSearchTimeout;
			statusTimer.Elapsed += new System.Timers.ElapsedEventHandler(statusTimer_Elapsed);
			statusTimer.AutoReset = true;
        }
        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
		/// <param name="disposing">Are we?</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                if (components != null)
                {
                    components.Dispose();
                }
            }
            base.Dispose(disposing);
        }

		#endregion

        #region Windows Designer generated code
        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
			this.components = new System.ComponentModel.Container();
			System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Example));
			this.buttValveTest = new System.Windows.Forms.Button();
			this.buttLeftSyringeTest = new System.Windows.Forms.Button();
			this.buttZeroLeftSensor = new System.Windows.Forms.Button();
			this.buttZeroRightSensor = new System.Windows.Forms.Button();
			this.tbLeftSensorPressure = new System.Windows.Forms.TextBox();
			this.tbRightSensorPressure = new System.Windows.Forms.TextBox();
			this.bar = new System.Windows.Forms.Label();
			this.label2 = new System.Windows.Forms.Label();
			this.ilLEDs = new System.Windows.Forms.ImageList(this.components);
			this.pbValveLED = new System.Windows.Forms.PictureBox();
			this.pbLeftSyringeLED = new System.Windows.Forms.PictureBox();
			this.pbLeftSensorLED = new System.Windows.Forms.PictureBox();
			this.pbRightSensorLED = new System.Windows.Forms.PictureBox();
			this.pbConnected = new System.Windows.Forms.PictureBox();
			this.pbBeaconStatus = new System.Windows.Forms.PictureBox();
			this.label1 = new System.Windows.Forms.Label();
			this.label3 = new System.Windows.Forms.Label();
			this.label4 = new System.Windows.Forms.Label();
			this.pbLFV_R = new System.Windows.Forms.PictureBox();
			this.pbLFV_N = new System.Windows.Forms.PictureBox();
			this.pbLFV_G = new System.Windows.Forms.PictureBox();
			this.label5 = new System.Windows.Forms.Label();
			this.label6 = new System.Windows.Forms.Label();
			this.label7 = new System.Windows.Forms.Label();
			this.label8 = new System.Windows.Forms.Label();
			this.label9 = new System.Windows.Forms.Label();
			this.label10 = new System.Windows.Forms.Label();
			this.pbRFV_G = new System.Windows.Forms.PictureBox();
			this.pbRFV_N = new System.Windows.Forms.PictureBox();
			this.pbRFV_R = new System.Windows.Forms.PictureBox();
			this.label11 = new System.Windows.Forms.Label();
			this.label12 = new System.Windows.Forms.Label();
			this.tbLeftHeldVolume = new System.Windows.Forms.TextBox();
			this.tbRightHeldVolume = new System.Windows.Forms.TextBox();
			this.label13 = new System.Windows.Forms.Label();
			this.label14 = new System.Windows.Forms.Label();
			this.buttHome = new System.Windows.Forms.Button();
			this.pbHome = new System.Windows.Forms.PictureBox();
			this.tbCurrentSerialNumber = new System.Windows.Forms.TextBox();
			this.label16 = new System.Windows.Forms.Label();
			this.buttRightSyringeTest = new System.Windows.Forms.Button();
			this.pbRightSyringeLED = new System.Windows.Forms.PictureBox();
			this.label17 = new System.Windows.Forms.Label();
			this.label18 = new System.Windows.Forms.Label();
			this.AboutButton = new System.Windows.Forms.Button();
			this.ConnectStatlbl = new System.Windows.Forms.Label();
			this.VersionInfo = new System.Windows.Forms.Label();
			this.textBoxErrorState = new System.Windows.Forms.TextBox();
			this.label19 = new System.Windows.Forms.Label();
			this.ConnectedInstrumentName = new System.Windows.Forms.Label();
			this.RightValvePictureBox = new System.Windows.Forms.PictureBox();
			this.MachinePictureBox = new System.Windows.Forms.PictureBox();
			this.LeftModuleLED = new System.Windows.Forms.PictureBox();
			this.RightModuleLED = new System.Windows.Forms.PictureBox();
			this.SingleModuleLED = new System.Windows.Forms.PictureBox();
			this.DeviceImageList = new System.Windows.Forms.ImageList(this.components);
			this.LeftValvePictureBox = new System.Windows.Forms.PictureBox();
			this.LargeMachinePictureBox = new System.Windows.Forms.PictureBox();
			this.PumpImageList = new System.Windows.Forms.ImageList(this.components);
			this.TestPanel = new System.Windows.Forms.Panel();
			this.panel1 = new System.Windows.Forms.Panel();
			this.PowerQuestionLabel = new System.Windows.Forms.Label();
			this.ProgramQuestionLabel = new System.Windows.Forms.Label();
			this.label15 = new System.Windows.Forms.Label();
			((System.ComponentModel.ISupportInitialize)(this.pbValveLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLeftSyringeLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLeftSensorLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRightSensorLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbConnected)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbBeaconStatus)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLFV_R)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLFV_N)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLFV_G)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRFV_G)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRFV_N)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRFV_R)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbHome)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRightSyringeLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.RightValvePictureBox)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.MachinePictureBox)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.LeftModuleLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.RightModuleLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.SingleModuleLED)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.LeftValvePictureBox)).BeginInit();
			((System.ComponentModel.ISupportInitialize)(this.LargeMachinePictureBox)).BeginInit();
			this.TestPanel.SuspendLayout();
			this.panel1.SuspendLayout();
			this.SuspendLayout();
			// 
			// buttValveTest
			// 
			this.buttValveTest.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.buttValveTest.CausesValidation = false;
			this.buttValveTest.FlatStyle = System.Windows.Forms.FlatStyle.System;
			this.buttValveTest.Location = new System.Drawing.Point(6, 245);
			this.buttValveTest.Name = "buttValveTest";
			this.buttValveTest.Size = new System.Drawing.Size(136, 32);
			this.buttValveTest.TabIndex = 3;
			this.buttValveTest.Text = "Valve Test";
			this.buttValveTest.Click += new System.EventHandler(this.buttValveTest_Click);
			// 
			// buttLeftSyringeTest
			// 
			this.buttLeftSyringeTest.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.buttLeftSyringeTest.CausesValidation = false;
			this.buttLeftSyringeTest.Location = new System.Drawing.Point(6, 317);
			this.buttLeftSyringeTest.Name = "buttLeftSyringeTest";
			this.buttLeftSyringeTest.Size = new System.Drawing.Size(136, 32);
			this.buttLeftSyringeTest.TabIndex = 4;
			this.buttLeftSyringeTest.Text = "Left Syringe Test";
			this.buttLeftSyringeTest.Click += new System.EventHandler(this.buttLeftSyringeTest_Click);
			// 
			// buttZeroLeftSensor
			// 
			this.buttZeroLeftSensor.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.buttZeroLeftSensor.CausesValidation = false;
			this.buttZeroLeftSensor.Location = new System.Drawing.Point(6, 389);
			this.buttZeroLeftSensor.Name = "buttZeroLeftSensor";
			this.buttZeroLeftSensor.Size = new System.Drawing.Size(136, 32);
			this.buttZeroLeftSensor.TabIndex = 6;
			this.buttZeroLeftSensor.Text = "Zero Left Sensor";
			this.buttZeroLeftSensor.Click += new System.EventHandler(this.buttZeroLeftSensor_Click);
			// 
			// buttZeroRightSensor
			// 
			this.buttZeroRightSensor.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.buttZeroRightSensor.CausesValidation = false;
			this.buttZeroRightSensor.Location = new System.Drawing.Point(342, 389);
			this.buttZeroRightSensor.Name = "buttZeroRightSensor";
			this.buttZeroRightSensor.Size = new System.Drawing.Size(136, 32);
			this.buttZeroRightSensor.TabIndex = 7;
			this.buttZeroRightSensor.Text = "Zero Right Sensor";
			this.buttZeroRightSensor.Click += new System.EventHandler(this.buttZeroRightSensor_Click);
			// 
			// tbLeftSensorPressure
			// 
			this.tbLeftSensorPressure.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.tbLeftSensorPressure.Location = new System.Drawing.Point(189, 397);
			this.tbLeftSensorPressure.Name = "tbLeftSensorPressure";
			this.tbLeftSensorPressure.ReadOnly = true;
			this.tbLeftSensorPressure.Size = new System.Drawing.Size(88, 22);
			this.tbLeftSensorPressure.TabIndex = 5;
			this.tbLeftSensorPressure.TextAlign = System.Windows.Forms.HorizontalAlignment.Right;
			// 
			// tbRightSensorPressure
			// 
			this.tbRightSensorPressure.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.tbRightSensorPressure.Location = new System.Drawing.Point(518, 397);
			this.tbRightSensorPressure.Name = "tbRightSensorPressure";
			this.tbRightSensorPressure.ReadOnly = true;
			this.tbRightSensorPressure.Size = new System.Drawing.Size(88, 22);
			this.tbRightSensorPressure.TabIndex = 6;
			this.tbRightSensorPressure.TextAlign = System.Windows.Forms.HorizontalAlignment.Right;
			// 
			// bar
			// 
			this.bar.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.bar.Location = new System.Drawing.Point(285, 397);
			this.bar.Name = "bar";
			this.bar.Size = new System.Drawing.Size(32, 24);
			this.bar.TabIndex = 9;
			this.bar.Text = "bar";
			this.bar.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
			// 
			// label2
			// 
			this.label2.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label2.Location = new System.Drawing.Point(614, 397);
			this.label2.Name = "label2";
			this.label2.Size = new System.Drawing.Size(33, 24);
			this.label2.TabIndex = 10;
			this.label2.Text = "bar";
			this.label2.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
			// 
			// ilLEDs
			// 
			this.ilLEDs.ImageStream = ((System.Windows.Forms.ImageListStreamer)(resources.GetObject("ilLEDs.ImageStream")));
			this.ilLEDs.TransparentColor = System.Drawing.Color.Transparent;
			this.ilLEDs.Images.SetKeyName(0, "");
			this.ilLEDs.Images.SetKeyName(1, "");
			this.ilLEDs.Images.SetKeyName(2, "");
			this.ilLEDs.Images.SetKeyName(3, "");
			this.ilLEDs.Images.SetKeyName(4, "");
			this.ilLEDs.Images.SetKeyName(5, "");
			// 
			// pbValveLED
			// 
			this.pbValveLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbValveLED.Location = new System.Drawing.Point(150, 253);
			this.pbValveLED.Name = "pbValveLED";
			this.pbValveLED.Size = new System.Drawing.Size(16, 16);
			this.pbValveLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbValveLED.TabIndex = 13;
			this.pbValveLED.TabStop = false;
			// 
			// pbLeftSyringeLED
			// 
			this.pbLeftSyringeLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbLeftSyringeLED.Location = new System.Drawing.Point(150, 325);
			this.pbLeftSyringeLED.Name = "pbLeftSyringeLED";
			this.pbLeftSyringeLED.Size = new System.Drawing.Size(16, 16);
			this.pbLeftSyringeLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbLeftSyringeLED.TabIndex = 14;
			this.pbLeftSyringeLED.TabStop = false;
			// 
			// pbLeftSensorLED
			// 
			this.pbLeftSensorLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbLeftSensorLED.Location = new System.Drawing.Point(150, 397);
			this.pbLeftSensorLED.Name = "pbLeftSensorLED";
			this.pbLeftSensorLED.Size = new System.Drawing.Size(16, 16);
			this.pbLeftSensorLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbLeftSensorLED.TabIndex = 15;
			this.pbLeftSensorLED.TabStop = false;
			// 
			// pbRightSensorLED
			// 
			this.pbRightSensorLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbRightSensorLED.Location = new System.Drawing.Point(486, 397);
			this.pbRightSensorLED.Name = "pbRightSensorLED";
			this.pbRightSensorLED.Size = new System.Drawing.Size(16, 16);
			this.pbRightSensorLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbRightSensorLED.TabIndex = 16;
			this.pbRightSensorLED.TabStop = false;
			// 
			// pbConnected
			// 
			this.pbConnected.Location = new System.Drawing.Point(624, 45);
			this.pbConnected.Name = "pbConnected";
			this.pbConnected.Size = new System.Drawing.Size(16, 16);
			this.pbConnected.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbConnected.TabIndex = 18;
			this.pbConnected.TabStop = false;
			// 
			// pbBeaconStatus
			// 
			this.pbBeaconStatus.Location = new System.Drawing.Point(624, 21);
			this.pbBeaconStatus.Name = "pbBeaconStatus";
			this.pbBeaconStatus.Size = new System.Drawing.Size(16, 16);
			this.pbBeaconStatus.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbBeaconStatus.TabIndex = 19;
			this.pbBeaconStatus.TabStop = false;
			// 
			// label1
			// 
			this.label1.Location = new System.Drawing.Point(520, 13);
			this.label1.Name = "label1";
			this.label1.Size = new System.Drawing.Size(96, 32);
			this.label1.TabIndex = 20;
			this.label1.Text = "Status Beacon";
			this.label1.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label3
			// 
			this.label3.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label3.Location = new System.Drawing.Point(194, 229);
			this.label3.Name = "label3";
			this.label3.Size = new System.Drawing.Size(110, 16);
			this.label3.TabIndex = 21;
			this.label3.Text = "Left Valve Pos";
			this.label3.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label4
			// 
			this.label4.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label4.Location = new System.Drawing.Point(518, 229);
			this.label4.Name = "label4";
			this.label4.Size = new System.Drawing.Size(110, 16);
			this.label4.TabIndex = 22;
			this.label4.Text = "Right Valve Pos";
			this.label4.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// pbLFV_R
			// 
			this.pbLFV_R.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbLFV_R.Location = new System.Drawing.Point(201, 253);
			this.pbLFV_R.Name = "pbLFV_R";
			this.pbLFV_R.Size = new System.Drawing.Size(16, 16);
			this.pbLFV_R.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbLFV_R.TabIndex = 23;
			this.pbLFV_R.TabStop = false;
			// 
			// pbLFV_N
			// 
			this.pbLFV_N.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbLFV_N.Location = new System.Drawing.Point(249, 253);
			this.pbLFV_N.Name = "pbLFV_N";
			this.pbLFV_N.Size = new System.Drawing.Size(16, 16);
			this.pbLFV_N.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbLFV_N.TabIndex = 24;
			this.pbLFV_N.TabStop = false;
			// 
			// pbLFV_G
			// 
			this.pbLFV_G.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbLFV_G.Location = new System.Drawing.Point(297, 253);
			this.pbLFV_G.Name = "pbLFV_G";
			this.pbLFV_G.Size = new System.Drawing.Size(16, 16);
			this.pbLFV_G.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbLFV_G.TabIndex = 25;
			this.pbLFV_G.TabStop = false;
			// 
			// label5
			// 
			this.label5.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label5.Location = new System.Drawing.Point(177, 253);
			this.label5.Name = "label5";
			this.label5.Size = new System.Drawing.Size(24, 16);
			this.label5.TabIndex = 26;
			this.label5.Text = "R";
			this.label5.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label6
			// 
			this.label6.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label6.Location = new System.Drawing.Point(225, 253);
			this.label6.Name = "label6";
			this.label6.Size = new System.Drawing.Size(24, 16);
			this.label6.TabIndex = 27;
			this.label6.Text = "N";
			this.label6.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label7
			// 
			this.label7.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label7.Location = new System.Drawing.Point(273, 253);
			this.label7.Name = "label7";
			this.label7.Size = new System.Drawing.Size(24, 16);
			this.label7.TabIndex = 28;
			this.label7.Text = "A";
			this.label7.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label8
			// 
			this.label8.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label8.Location = new System.Drawing.Point(597, 253);
			this.label8.Name = "label8";
			this.label8.Size = new System.Drawing.Size(24, 16);
			this.label8.TabIndex = 34;
			this.label8.Text = "A";
			this.label8.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label9
			// 
			this.label9.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label9.Location = new System.Drawing.Point(549, 253);
			this.label9.Name = "label9";
			this.label9.Size = new System.Drawing.Size(24, 16);
			this.label9.TabIndex = 33;
			this.label9.Text = "N";
			this.label9.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label10
			// 
			this.label10.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label10.Location = new System.Drawing.Point(501, 253);
			this.label10.Name = "label10";
			this.label10.Size = new System.Drawing.Size(24, 16);
			this.label10.TabIndex = 32;
			this.label10.Text = "R";
			this.label10.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// pbRFV_G
			// 
			this.pbRFV_G.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbRFV_G.Location = new System.Drawing.Point(621, 253);
			this.pbRFV_G.Name = "pbRFV_G";
			this.pbRFV_G.Size = new System.Drawing.Size(16, 16);
			this.pbRFV_G.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbRFV_G.TabIndex = 31;
			this.pbRFV_G.TabStop = false;
			// 
			// pbRFV_N
			// 
			this.pbRFV_N.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbRFV_N.Location = new System.Drawing.Point(573, 253);
			this.pbRFV_N.Name = "pbRFV_N";
			this.pbRFV_N.Size = new System.Drawing.Size(16, 16);
			this.pbRFV_N.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbRFV_N.TabIndex = 30;
			this.pbRFV_N.TabStop = false;
			// 
			// pbRFV_R
			// 
			this.pbRFV_R.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbRFV_R.Location = new System.Drawing.Point(525, 253);
			this.pbRFV_R.Name = "pbRFV_R";
			this.pbRFV_R.Size = new System.Drawing.Size(16, 16);
			this.pbRFV_R.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbRFV_R.TabIndex = 29;
			this.pbRFV_R.TabStop = false;
			// 
			// label11
			// 
			this.label11.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label11.Location = new System.Drawing.Point(181, 301);
			this.label11.Name = "label11";
			this.label11.Size = new System.Drawing.Size(112, 16);
			this.label11.TabIndex = 35;
			this.label11.Text = "Left Held Volume";
			this.label11.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label12
			// 
			this.label12.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label12.Location = new System.Drawing.Point(510, 301);
			this.label12.Name = "label12";
			this.label12.Size = new System.Drawing.Size(120, 16);
			this.label12.TabIndex = 36;
			this.label12.Text = "Right Held Volume";
			this.label12.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// tbLeftHeldVolume
			// 
			this.tbLeftHeldVolume.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.tbLeftHeldVolume.Location = new System.Drawing.Point(189, 325);
			this.tbLeftHeldVolume.Name = "tbLeftHeldVolume";
			this.tbLeftHeldVolume.ReadOnly = true;
			this.tbLeftHeldVolume.Size = new System.Drawing.Size(88, 22);
			this.tbLeftHeldVolume.TabIndex = 37;
			this.tbLeftHeldVolume.TextAlign = System.Windows.Forms.HorizontalAlignment.Right;
			// 
			// tbRightHeldVolume
			// 
			this.tbRightHeldVolume.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.tbRightHeldVolume.Location = new System.Drawing.Point(518, 325);
			this.tbRightHeldVolume.Name = "tbRightHeldVolume";
			this.tbRightHeldVolume.ReadOnly = true;
			this.tbRightHeldVolume.Size = new System.Drawing.Size(88, 22);
			this.tbRightHeldVolume.TabIndex = 38;
			this.tbRightHeldVolume.TextAlign = System.Windows.Forms.HorizontalAlignment.Right;
			// 
			// label13
			// 
			this.label13.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label13.Location = new System.Drawing.Point(285, 325);
			this.label13.Name = "label13";
			this.label13.Size = new System.Drawing.Size(24, 24);
			this.label13.TabIndex = 39;
			this.label13.Text = "µL";
			this.label13.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
			// 
			// label14
			// 
			this.label14.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label14.Location = new System.Drawing.Point(614, 325);
			this.label14.Name = "label14";
			this.label14.Size = new System.Drawing.Size(24, 24);
			this.label14.TabIndex = 40;
			this.label14.Text = "µL";
			this.label14.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
			// 
			// buttHome
			// 
			this.buttHome.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.buttHome.CausesValidation = false;
			this.buttHome.Location = new System.Drawing.Point(6, 197);
			this.buttHome.Name = "buttHome";
			this.buttHome.Size = new System.Drawing.Size(136, 32);
			this.buttHome.TabIndex = 2;
			this.buttHome.Text = "Home";
			this.buttHome.Click += new System.EventHandler(this.buttHome_Click);
			// 
			// pbHome
			// 
			this.pbHome.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbHome.Location = new System.Drawing.Point(150, 205);
			this.pbHome.Name = "pbHome";
			this.pbHome.Size = new System.Drawing.Size(16, 16);
			this.pbHome.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbHome.TabIndex = 42;
			this.pbHome.TabStop = false;
			// 
			// tbCurrentSerialNumber
			// 
			this.tbCurrentSerialNumber.Anchor = System.Windows.Forms.AnchorStyles.Top;
			this.tbCurrentSerialNumber.Font = new System.Drawing.Font("Microsoft Sans Serif", 20.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.tbCurrentSerialNumber.Location = new System.Drawing.Point(183, 13);
			this.tbCurrentSerialNumber.Name = "tbCurrentSerialNumber";
			this.tbCurrentSerialNumber.ReadOnly = true;
			this.tbCurrentSerialNumber.Size = new System.Drawing.Size(162, 38);
			this.tbCurrentSerialNumber.TabIndex = 44;
			this.tbCurrentSerialNumber.TabStop = false;
			// 
			// label16
			// 
			this.label16.Anchor = System.Windows.Forms.AnchorStyles.Top;
			this.label16.Location = new System.Drawing.Point(7, 21);
			this.label16.Name = "label16";
			this.label16.Size = new System.Drawing.Size(136, 24);
			this.label16.TabIndex = 45;
			this.label16.Text = "Instrument Serial No.";
			this.label16.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// buttRightSyringeTest
			// 
			this.buttRightSyringeTest.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.buttRightSyringeTest.CausesValidation = false;
			this.buttRightSyringeTest.Location = new System.Drawing.Point(342, 317);
			this.buttRightSyringeTest.Name = "buttRightSyringeTest";
			this.buttRightSyringeTest.Size = new System.Drawing.Size(136, 32);
			this.buttRightSyringeTest.TabIndex = 5;
			this.buttRightSyringeTest.Text = "Right Syringe Test";
			this.buttRightSyringeTest.Click += new System.EventHandler(this.buttRightsyringeTest_Click);
			// 
			// pbRightSyringeLED
			// 
			this.pbRightSyringeLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.pbRightSyringeLED.Location = new System.Drawing.Point(486, 325);
			this.pbRightSyringeLED.Name = "pbRightSyringeLED";
			this.pbRightSyringeLED.Size = new System.Drawing.Size(16, 16);
			this.pbRightSyringeLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.pbRightSyringeLED.TabIndex = 47;
			this.pbRightSyringeLED.TabStop = false;
			// 
			// label17
			// 
			this.label17.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label17.Location = new System.Drawing.Point(179, 373);
			this.label17.Name = "label17";
			this.label17.Size = new System.Drawing.Size(112, 16);
			this.label17.TabIndex = 48;
			this.label17.Text = "Left Pressure";
			this.label17.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// label18
			// 
			this.label18.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.label18.Location = new System.Drawing.Point(518, 373);
			this.label18.Name = "label18";
			this.label18.Size = new System.Drawing.Size(112, 16);
			this.label18.TabIndex = 49;
			this.label18.Text = "Right Pressure";
			this.label18.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
			// 
			// AboutButton
			// 
			this.AboutButton.Location = new System.Drawing.Point(552, 553);
			this.AboutButton.Name = "AboutButton";
			this.AboutButton.Size = new System.Drawing.Size(80, 24);
			this.AboutButton.TabIndex = 8;
			this.AboutButton.Text = "About...";
			this.AboutButton.Click += new System.EventHandler(this.AboutButton_Click);
			// 
			// ConnectStatlbl
			// 
			this.ConnectStatlbl.Location = new System.Drawing.Point(344, 45);
			this.ConnectStatlbl.Name = "ConnectStatlbl";
			this.ConnectStatlbl.Size = new System.Drawing.Size(272, 23);
			this.ConnectStatlbl.TabIndex = 51;
			this.ConnectStatlbl.Text = "label19";
			this.ConnectStatlbl.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
			// 
			// VersionInfo
			// 
			this.VersionInfo.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left)));
			this.VersionInfo.Font = new System.Drawing.Font("Microsoft Sans Serif", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.VersionInfo.Location = new System.Drawing.Point(367, 42);
			this.VersionInfo.Name = "VersionInfo";
			this.VersionInfo.Size = new System.Drawing.Size(272, 24);
			this.VersionInfo.TabIndex = 52;
			this.VersionInfo.Text = "label19";
			this.VersionInfo.TextAlign = System.Drawing.ContentAlignment.TopRight;
			// 
			// textBoxErrorState
			// 
			this.textBoxErrorState.Font = new System.Drawing.Font("Tahoma", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.textBoxErrorState.Location = new System.Drawing.Point(272, 518);
			this.textBoxErrorState.Multiline = true;
			this.textBoxErrorState.Name = "textBoxErrorState";
			this.textBoxErrorState.ReadOnly = true;
			this.textBoxErrorState.Size = new System.Drawing.Size(249, 58);
			this.textBoxErrorState.TabIndex = 53;
			this.textBoxErrorState.TextAlign = System.Windows.Forms.HorizontalAlignment.Center;
			// 
			// label19
			// 
			this.label19.Location = new System.Drawing.Point(141, 537);
			this.label19.Name = "label19";
			this.label19.Size = new System.Drawing.Size(125, 22);
			this.label19.TabIndex = 54;
			this.label19.Text = "Current Error Code";
			this.label19.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
			// 
			// ConnectedInstrumentName
			// 
			this.ConnectedInstrumentName.Anchor = System.Windows.Forms.AnchorStyles.Top;
			this.ConnectedInstrumentName.Font = new System.Drawing.Font("Tahoma", 20.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.ConnectedInstrumentName.Location = new System.Drawing.Point(367, 11);
			this.ConnectedInstrumentName.Name = "ConnectedInstrumentName";
			this.ConnectedInstrumentName.Size = new System.Drawing.Size(272, 29);
			this.ConnectedInstrumentName.TabIndex = 56;
			this.ConnectedInstrumentName.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
			// 
			// RightValvePictureBox
			// 
			this.RightValvePictureBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.RightValvePictureBox.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
			this.RightValvePictureBox.Location = new System.Drawing.Point(523, 121);
			this.RightValvePictureBox.Name = "RightValvePictureBox";
			this.RightValvePictureBox.Size = new System.Drawing.Size(100, 100);
			this.RightValvePictureBox.SizeMode = System.Windows.Forms.PictureBoxSizeMode.StretchImage;
			this.RightValvePictureBox.TabIndex = 59;
			this.RightValvePictureBox.TabStop = false;
			// 
			// MachinePictureBox
			// 
			this.MachinePictureBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.MachinePictureBox.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
			this.MachinePictureBox.Location = new System.Drawing.Point(26, 69);
			this.MachinePictureBox.Name = "MachinePictureBox";
			this.MachinePictureBox.Size = new System.Drawing.Size(100, 100);
			this.MachinePictureBox.SizeMode = System.Windows.Forms.PictureBoxSizeMode.CenterImage;
			this.MachinePictureBox.TabIndex = 60;
			this.MachinePictureBox.TabStop = false;
			this.MachinePictureBox.Visible = false;
			// 
			// LeftModuleLED
			// 
			this.LeftModuleLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.LeftModuleLED.Location = new System.Drawing.Point(376, 229);
			this.LeftModuleLED.Name = "LeftModuleLED";
			this.LeftModuleLED.Size = new System.Drawing.Size(16, 16);
			this.LeftModuleLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.LeftModuleLED.TabIndex = 61;
			this.LeftModuleLED.TabStop = false;
			// 
			// RightModuleLED
			// 
			this.RightModuleLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.RightModuleLED.Location = new System.Drawing.Point(426, 229);
			this.RightModuleLED.Name = "RightModuleLED";
			this.RightModuleLED.Size = new System.Drawing.Size(16, 16);
			this.RightModuleLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.RightModuleLED.TabIndex = 62;
			this.RightModuleLED.TabStop = false;
			// 
			// SingleModuleLED
			// 
			this.SingleModuleLED.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.SingleModuleLED.Location = new System.Drawing.Point(401, 229);
			this.SingleModuleLED.Name = "SingleModuleLED";
			this.SingleModuleLED.Size = new System.Drawing.Size(16, 16);
			this.SingleModuleLED.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
			this.SingleModuleLED.TabIndex = 63;
			this.SingleModuleLED.TabStop = false;
			// 
			// DeviceImageList
			// 
			this.DeviceImageList.ImageStream = ((System.Windows.Forms.ImageListStreamer)(resources.GetObject("DeviceImageList.ImageStream")));
			this.DeviceImageList.TransparentColor = System.Drawing.Color.Transparent;
			this.DeviceImageList.Images.SetKeyName(0, "4060.jpg");
			this.DeviceImageList.Images.SetKeyName(1, "4260.jpg");
			this.DeviceImageList.Images.SetKeyName(2, "402 valve.jpg");
			this.DeviceImageList.Images.SetKeyName(3, "406 Valve.jpg");
			this.DeviceImageList.Images.SetKeyName(4, "Tee valve.jpg");
			// 
			// LeftValvePictureBox
			// 
			this.LeftValvePictureBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.LeftValvePictureBox.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
			this.LeftValvePictureBox.Location = new System.Drawing.Point(199, 121);
			this.LeftValvePictureBox.Name = "LeftValvePictureBox";
			this.LeftValvePictureBox.Size = new System.Drawing.Size(100, 100);
			this.LeftValvePictureBox.SizeMode = System.Windows.Forms.PictureBoxSizeMode.StretchImage;
			this.LeftValvePictureBox.TabIndex = 64;
			this.LeftValvePictureBox.TabStop = false;
			// 
			// LargeMachinePictureBox
			// 
			this.LargeMachinePictureBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom;
			this.LargeMachinePictureBox.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
			this.LargeMachinePictureBox.Location = new System.Drawing.Point(346, 71);
			this.LargeMachinePictureBox.Name = "LargeMachinePictureBox";
			this.LargeMachinePictureBox.Size = new System.Drawing.Size(125, 150);
			this.LargeMachinePictureBox.SizeMode = System.Windows.Forms.PictureBoxSizeMode.StretchImage;
			this.LargeMachinePictureBox.TabIndex = 65;
			this.LargeMachinePictureBox.TabStop = false;
			// 
			// PumpImageList
			// 
			this.PumpImageList.ImageStream = ((System.Windows.Forms.ImageListStreamer)(resources.GetObject("PumpImageList.ImageStream")));
			this.PumpImageList.TransparentColor = System.Drawing.Color.Transparent;
			this.PumpImageList.Images.SetKeyName(0, "4020.jpg");
			this.PumpImageList.Images.SetKeyName(1, "4220.jpg");
			this.PumpImageList.Images.SetKeyName(2, "4220.jpg");
			this.PumpImageList.Images.SetKeyName(3, "4060.jpg");
			this.PumpImageList.Images.SetKeyName(4, "4260.jpg");
			this.PumpImageList.Images.SetKeyName(5, "Unknown.jpg");
			// 
			// TestPanel
			// 
			this.TestPanel.Controls.Add(this.MachinePictureBox);
			this.TestPanel.Controls.Add(this.LargeMachinePictureBox);
			this.TestPanel.Controls.Add(this.buttValveTest);
			this.TestPanel.Controls.Add(this.ConnectedInstrumentName);
			this.TestPanel.Controls.Add(this.LeftValvePictureBox);
			this.TestPanel.Controls.Add(this.buttLeftSyringeTest);
			this.TestPanel.Controls.Add(this.SingleModuleLED);
			this.TestPanel.Controls.Add(this.VersionInfo);
			this.TestPanel.Controls.Add(this.buttZeroLeftSensor);
			this.TestPanel.Controls.Add(this.RightModuleLED);
			this.TestPanel.Controls.Add(this.buttZeroRightSensor);
			this.TestPanel.Controls.Add(this.label16);
			this.TestPanel.Controls.Add(this.LeftModuleLED);
			this.TestPanel.Controls.Add(this.tbCurrentSerialNumber);
			this.TestPanel.Controls.Add(this.tbLeftSensorPressure);
			this.TestPanel.Controls.Add(this.tbRightSensorPressure);
			this.TestPanel.Controls.Add(this.RightValvePictureBox);
			this.TestPanel.Controls.Add(this.bar);
			this.TestPanel.Controls.Add(this.label2);
			this.TestPanel.Controls.Add(this.pbValveLED);
			this.TestPanel.Controls.Add(this.pbLeftSyringeLED);
			this.TestPanel.Controls.Add(this.pbLeftSensorLED);
			this.TestPanel.Controls.Add(this.pbRightSensorLED);
			this.TestPanel.Controls.Add(this.label3);
			this.TestPanel.Controls.Add(this.label4);
			this.TestPanel.Controls.Add(this.pbLFV_R);
			this.TestPanel.Controls.Add(this.label18);
			this.TestPanel.Controls.Add(this.pbLFV_N);
			this.TestPanel.Controls.Add(this.label17);
			this.TestPanel.Controls.Add(this.pbLFV_G);
			this.TestPanel.Controls.Add(this.pbRightSyringeLED);
			this.TestPanel.Controls.Add(this.label5);
			this.TestPanel.Controls.Add(this.buttRightSyringeTest);
			this.TestPanel.Controls.Add(this.label6);
			this.TestPanel.Controls.Add(this.label7);
			this.TestPanel.Controls.Add(this.pbRFV_R);
			this.TestPanel.Controls.Add(this.pbRFV_N);
			this.TestPanel.Controls.Add(this.pbHome);
			this.TestPanel.Controls.Add(this.pbRFV_G);
			this.TestPanel.Controls.Add(this.buttHome);
			this.TestPanel.Controls.Add(this.label10);
			this.TestPanel.Controls.Add(this.label14);
			this.TestPanel.Controls.Add(this.label9);
			this.TestPanel.Controls.Add(this.label13);
			this.TestPanel.Controls.Add(this.label8);
			this.TestPanel.Controls.Add(this.tbRightHeldVolume);
			this.TestPanel.Controls.Add(this.label11);
			this.TestPanel.Controls.Add(this.tbLeftHeldVolume);
			this.TestPanel.Controls.Add(this.label12);
			this.TestPanel.Location = new System.Drawing.Point(1, 70);
			this.TestPanel.Name = "TestPanel";
			this.TestPanel.Size = new System.Drawing.Size(655, 431);
			this.TestPanel.TabIndex = 66;
			// 
			// panel1
			// 
			this.panel1.Controls.Add(this.PowerQuestionLabel);
			this.panel1.Controls.Add(this.ProgramQuestionLabel);
			this.panel1.Controls.Add(this.label15);
			this.panel1.Location = new System.Drawing.Point(127, 112);
			this.panel1.Name = "panel1";
			this.panel1.Size = new System.Drawing.Size(400, 300);
			this.panel1.TabIndex = 67;
			// 
			// PowerQuestionLabel
			// 
			this.PowerQuestionLabel.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
			this.PowerQuestionLabel.AutoSize = true;
			this.PowerQuestionLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.PowerQuestionLabel.ForeColor = System.Drawing.Color.Red;
			this.PowerQuestionLabel.Location = new System.Drawing.Point(70, 229);
			this.PowerQuestionLabel.Name = "PowerQuestionLabel";
			this.PowerQuestionLabel.Size = new System.Drawing.Size(261, 24);
			this.PowerQuestionLabel.TabIndex = 2;
			this.PowerQuestionLabel.Text = "Did you POWER CYCLE unit?";
			this.PowerQuestionLabel.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			this.PowerQuestionLabel.Visible = false;
			// 
			// ProgramQuestionLabel
			// 
			this.ProgramQuestionLabel.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
			this.ProgramQuestionLabel.AutoSize = true;
			this.ProgramQuestionLabel.Font = new System.Drawing.Font("Microsoft Sans Serif", 14.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.ProgramQuestionLabel.ForeColor = System.Drawing.Color.Red;
			this.ProgramQuestionLabel.Location = new System.Drawing.Point(60, 193);
			this.ProgramQuestionLabel.Name = "ProgramQuestionLabel";
			this.ProgramQuestionLabel.Size = new System.Drawing.Size(281, 24);
			this.ProgramQuestionLabel.TabIndex = 1;
			this.ProgramQuestionLabel.Text = "Did you PROGRAM USB board?";
			this.ProgramQuestionLabel.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			this.ProgramQuestionLabel.Visible = false;
			// 
			// label15
			// 
			this.label15.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
			this.label15.AutoSize = true;
			this.label15.Font = new System.Drawing.Font("Microsoft Sans Serif", 18F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.label15.Location = new System.Drawing.Point(22, 142);
			this.label15.Name = "label15";
			this.label15.Size = new System.Drawing.Size(366, 29);
			this.label15.TabIndex = 0;
			this.label15.Text = "Waiting for instrument to connect.";
			this.label15.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
			// 
			// Example
			// 
			this.AutoScaleBaseSize = new System.Drawing.Size(6, 15);
			this.ClientSize = new System.Drawing.Size(660, 589);
			this.Controls.Add(this.TestPanel);
			this.Controls.Add(this.panel1);
			this.Controls.Add(this.label19);
			this.Controls.Add(this.textBoxErrorState);
			this.Controls.Add(this.ConnectStatlbl);
			this.Controls.Add(this.AboutButton);
			this.Controls.Add(this.label1);
			this.Controls.Add(this.pbBeaconStatus);
			this.Controls.Add(this.pbConnected);
			this.Font = new System.Drawing.Font("Microsoft Sans Serif", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
			this.Name = "Example";
			this.Text = "Verity 4000 Series Example GEARS";
			this.FormClosed += new System.Windows.Forms.FormClosedEventHandler(this.Example_FormClosed);
			this.Load += new System.EventHandler(this.Example_Load);
			((System.ComponentModel.ISupportInitialize)(this.pbValveLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLeftSyringeLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLeftSensorLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRightSensorLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbConnected)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbBeaconStatus)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLFV_R)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLFV_N)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbLFV_G)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRFV_G)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRFV_N)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRFV_R)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbHome)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.pbRightSyringeLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.RightValvePictureBox)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.MachinePictureBox)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.LeftModuleLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.RightModuleLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.SingleModuleLED)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.LeftValvePictureBox)).EndInit();
			((System.ComponentModel.ISupportInitialize)(this.LargeMachinePictureBox)).EndInit();
			this.TestPanel.ResumeLayout(false);
			this.TestPanel.PerformLayout();
			this.panel1.ResumeLayout(false);
			this.panel1.PerformLayout();
			this.ResumeLayout(false);
			this.PerformLayout();

        }
        #endregion

		#region MAIN and Events

		/// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main(string[] args)
        {
            commandLineArgs = args;
            Application.Run(new Example());
        }
        /// <summary>
        /// Check for GEARS running.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void Example_Load(object sender, System.EventArgs e)
        {
			System.Diagnostics.Process _MyProcess = System.Diagnostics.Process.GetCurrentProcess();
			System.Diagnostics.Process[] _List = System.Diagnostics.Process.GetProcesses();

			int _Count			= 0;
			string _ProcessName	= "GEARS Application";
			//--------------------------------------------------------------------------------
			// Make sure that there is at least one but no more than one _GEARSEngine running
			//--------------------------------------------------------------------------------
			foreach(System.Diagnostics.Process _Item in _List)
			{
				if ((_Item.ProcessName == _ProcessName) ||
					(_Item.ProcessName == (_ProcessName + ".vshost")) ||
					((_Item.ProcessName + ".vshost" ) == _ProcessName))
				{
					_Count++;
				}
			}
			//----------------------------------------------------------
			// If no GEARS Application running then tell them to run it
			//----------------------------------------------------------
			if (_Count == 0)
			{
				MessageBox.Show("Please run 'GEARS Application' before running this application.", "", MessageBoxButtons.OK, MessageBoxIcon.Warning);

				this.Close();
				return;
			}
        }
        /// <summary>
        /// Cleanup resources if closing.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
		private void Example_FormClosed(object sender, FormClosedEventArgs e)
        {
            beaconTimer.Enabled = false;
            try
            {
                if (beaconListener != null)
                    beaconListener.Stop();
            }
            catch
            {
            }
            try
            {
				if (currentGTCP != null)
				{
				    currentGTCP.Disconnect();
				    currentGTCP = null;
				}
            }
            catch
            {
            }
        }

		#endregion

		#region Communications

		/// <summary>
		/// Try to connect to a single instrumnet.
		/// </summary>
		/// <returns>True if successful</returns>
        private bool Connect()
        {
            bool retval = true;
            try
            {
                if (ConnectToInstrument())
                {
                    setLabeltext(LabelControls.Connect, "Connected");
					setLabeltext(LabelControls.ConnectedInstrumentName, currentInstrumentName);
					setLabeltext(LabelControls.ConnectedInstrumentFWVersion, "Firmware Version: " + currentFirmwareVersion);
                    setLEDImages(LEDControls.Connected, ilLEDs.Images[3]);
                    setButtonEnabledState(ButtonControls.Home, false);
                    setButtonEnabledState(ButtonControls.SetSerialNumber, false);
                }
                else
                {
                    retval = false;
                    lock (instrumentList)
                    {
                        instrumentList.Clear();
                    }
                }
            }
            catch (Exception ex)
            {
                setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
                MessageBox.Show("Error connecting to " + currentInstrumentName + ".  Error message: " + ex.Message);
            }
            return retval;
        }
		/// <summary>
		/// Wait for motors to finish for specified time.
		/// </summary>
		/// <param name="_Milliseconds">How long to wait.</param>
		/// <returns>True if all motors in good state.</returns>
		private bool WaitForMotors(int _Milliseconds)
		{
			bool _Return= false;
			newStatus	= false;
			int _Count	= (_Milliseconds < 10) ? 1 : ((_Milliseconds / 10) + 1);
			//-----------------------
			// Wait for two syringes
			//-----------------------
			if (!String.IsNullOrEmpty(rightInstrumentName))
			{
				for (int ii = 0; ii < _Count; ii++)
				{
					if ((ii % 10) == 0)
					{
						Application.DoEvents();
					}
					if (!newStatus)
					{
						Thread.Sleep(10);
					}
					else
					{
						newStatus	= false;

						if ((!leftValveMotor && (leftValveType != 0)) ||
							!leftSyringeMotor ||
							!rightSyringeMotor ||
							(!rightValveMotor && (rightValveType != 0)))
						{
							Thread.Sleep(10);
						}
						else
						{
							_Return	= true;
							break;
						}
					}
				}
			}
			else
			{
				for (int ii = 0; ii < _Count; ii++)
				{
					if ((ii % 10) == 0)
					{
						Application.DoEvents();
					}
					if (!newStatus)
					{
						Thread.Sleep(10);
					}
					else
					{
						newStatus	= false;

						if (!leftValveMotor ||
							!leftSyringeMotor)
						{
							Thread.Sleep(10);
						}
						else
						{
							_Return	= true;
							break;
						}
					}
				}
			}
			if (!_Return)
			{
				SendCommand("Get Error", connectedInstrument.Name, null, false, standardTimeout);
			}
			return(_Return);
		}
		/// <summary>
		/// Processes serial number for model type.
		/// </summary>
		/// <returns>Model type</returns>
		private int GetModelType()
		{
            int _Return = 5;
            string serialNo = tbCurrentSerialNumber.Text.ToUpper();
            Regex myRegex = new Regex(serialNumberFormat);
            serialNo = serialNo.ToUpper();

            if (myRegex.IsMatch(serialNo) && (serialNo.Length == 9))
            {
				string _ModelType	= serialNo.Substring(5, 1);

				if (modelTypesToLookFor.Contains(_ModelType))
				{
					string _Value	= (string)modelTypesToLookFor[_ModelType];

					int.TryParse(_Value, out _Return);
				}
			}
			return(_Return);
		}
		/// <summary>
		/// Processes serial number for valve type.
		/// </summary>
		/// <returns>Valve type</returns>
		private int GetValveType()
		{
            int _Return = 0;
            string serialNo = tbCurrentSerialNumber.Text.ToUpper();
            Regex myRegex = new Regex(serialNumberFormat);
            serialNo = serialNo.ToUpper();

            if (myRegex.IsMatch(serialNo) && (serialNo.Length == 9))
            {
				string _ModelType			= serialNo.Substring(5, 1);

				if (modelTypesToLookFor.Contains(_ModelType))
				{
					string _Value	= (string)modelTypesToLookFor[_ModelType];

					int.TryParse(_Value, out _Return);
				}
				switch(_Return)
				{
					case 0:	// 4020
					case 1:	// 4120
					case 2:	// 4220
						{
							_Return	= 2;
						}
						break;
					case 3:	// 4060
					case 4:	// 4260
						{
							_Return	= 3;
						}
						break;
				}
			}
			return(_Return);
		}

		#endregion

		#region Buttons

		/// <summary>
		/// About information.
		/// </summary>
		/// <param name="sender"></param>
		/// <param name="e"></param>
        private void AboutButton_Click(object sender, System.EventArgs e)
        {
            if (Cursors.WaitCursor == this.Cursor)
                return;
            About aboutBox = new About();
            aboutBox.ShowDialog();
        }
		/// <summary>
        /// Send Home command to device.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void buttHome_Click(object sender, System.EventArgs e)
        {
			//---------------------------------------------------------
			// If already waiting somewhere don't service button press
			//---------------------------------------------------------
            if (Cursors.WaitCursor == this.Cursor)
                return;
           
			this.Cursor = Cursors.WaitCursor;
			EnableButtons(false);
            setTextBoxText(TextControls.ErrorState, String.Empty);

            if (SendCommand("Home", connectedInstrument.Name, null, false, 30000L))
            {
                setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[3]);
                setLEDImages(LEDControls.LeftModuleLED, ilLEDs.Images[3]);
                setLEDImages(LEDControls.RightModuleLED, ilLEDs.Images[3]);

				WaitForMotors(60000);

                setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[4]);
                setLEDImages(LEDControls.LeftModuleLED, ilLEDs.Images[4]);
                setLEDImages(LEDControls.RightModuleLED, ilLEDs.Images[4]);

                EthernetParameterList ep2 = new EthernetParameterList();

                if (!SendCommand("Get Syringe Info", leftInstrumentName, ep2, false, standardTimeout))
                {
                    MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                }
				if (!String.IsNullOrEmpty(rightInstrumentName))
				{
					if (!SendCommand("Get Syringe Info", rightInstrumentName, ep2, false, standardTimeout))
					{
						MessageBox.Show(Messages[(int)Message.Error_communicating_with_right_syringe]);
					}
					Thread.Sleep(1000);
					Application.DoEvents();
				}
                if ((connectedInstrument.InstructionSet[leftInstrumentName].Commands["Get Pressure"] != null) && (!SendCommand("Get Pressure", leftInstrumentName, ep2, false, standardTimeout)))
                {
                    MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                }
				if (!String.IsNullOrEmpty(rightInstrumentName))
				{
					if ((connectedInstrument.InstructionSet[rightInstrumentName].Commands["Get Pressure"] != null) && (!SendCommand("Get Pressure", rightInstrumentName, ep2, false, standardTimeout)))
					{
						MessageBox.Show(Messages[(int)Message.Error_communicating_with_right_syringe]);
					}
					Thread.Sleep(1000);
					Application.DoEvents();
				}
                setLEDImages(LEDControls.Home, ilLEDs.Images[3]);
                setButtonEnabledState(ButtonControls.Home, true);
                setButtonEnabledState(ButtonControls.SetSerialNumber, true);
                setButtonEnabledState(ButtonControls.LeftSyringeTest, true);
                setButtonEnabledState(ButtonControls.RightSyringeTest, true);
                setButtonEnabledState(ButtonControls.ValveTest, true);
                setButtonEnabledState(ButtonControls.ZeroLeftSensor, true);
                setButtonEnabledState(ButtonControls.ZeroRightSensor, true);
            }
            else
            {
                MessageBox.Show("Error homing " + currentInstrumentName + ".");
                setLEDImages(LEDControls.Home, ilLEDs.Images[5]);
            }
            this.Cursor = Cursors.Default;
        }
        /// <summary>
        /// Perform valve test.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void buttValveTest_Click(object sender, System.EventArgs e)
        {
            if (Cursors.WaitCursor == this.Cursor)
                return;
            
			EthernetParameterList epl = new EthernetParameterList();
            EthernetParameter ep = new EthernetParameter();
            bool status = true;

            pbValveLED.Image = ilLEDs.Images[0];

            this.Cursor = Cursors.WaitCursor;

            Application.DoEvents();

			rightValvePosition	= string.Empty;
			leftValvePosition	= string.Empty;
			rightVolumne		= string.Empty;
			leftVolumne			= string.Empty;

			ClearValveVolume();

            #region Test Left Valve

            string setCommandName = "Valve Position";
            string getCommandName = "Get Syringe Info";
            string setParamName = "Position";
			int _Count	= GetValveType();

            for (int i = 0; i < _Count; i++)
            {
                if (!status)
                {
                    break;
                }
                switch (i)
                {
                    case 0:
                        epl.Clear();
                        ep.Name = setParamName;
                        ep.Value = "R";
                        epl.Add(ep);
                        if (!SendCommand(setCommandName, leftInstrumentName, epl, false, standardTimeout))
                        {
                            MessageBox.Show("ERROR: Setting" + setCommandName + " to : R.");
                            pbValveLED.Image = ilLEDs.Images[5];
                            status = false;
                        }
                        else
                        {
							newStatus	= false;
                        }
                        break;
                    case 1:
                        epl.Clear();
                        ep.Name = setParamName;
                        ep.Value = "N";
                        epl.Add(ep);
                        if (!SendCommand(setCommandName, leftInstrumentName, epl, false, standardTimeout))
                        {
                            MessageBox.Show("ERROR: Setting" + setCommandName + " to : N.");
                            pbValveLED.Image = ilLEDs.Images[5];
                            status = false;
                        }
                        else
                        {
							newStatus	= false;
                        }
                        break;
                    case 2:
                        epl.Clear();
                        ep.Name = setParamName;
                        ep.Value = "A";
                        epl.Add(ep);
                        if (!SendCommand(setCommandName, leftInstrumentName, epl, false, standardTimeout))
                        {
                            MessageBox.Show("ERROR: Setting" + setCommandName + " to : A.");
                            pbValveLED.Image = ilLEDs.Images[5];
                            status = false;
                        }
                        else
                        {
							newStatus	= false;
                        }
                        break;
                }
				for (int ii = 0; ii < 1000; ii++)	//int.MaxValue / 4; ii++)
				{
					if (!newStatus)
					{
						Thread.Sleep(10);
					}
					else
					{
						newStatus	= false;

						if (!leftValveMotor)
						{
							Thread.Sleep(10);
						}
						else
						{
							break;
						}
					}
				}
				epl.Clear();

				if (!SendCommand(getCommandName, leftInstrumentName, epl, false, standardTimeout))
				{
					MessageBox.Show("ERROR: " + getCommandName);
					pbValveLED.Image = ilLEDs.Images[5];
					status = false;
				}
				Thread.Sleep(1000);
                Application.DoEvents();
            }
            #endregion

			#region Test Right Valve

			if (!String.IsNullOrEmpty(rightInstrumentName) && (rightValveType != 0))
			{
				for (int i = 0; i < _Count; i++)
				{
					if (!status)
					{
						break;
					}
					switch (i)
					{
						case 0:
							epl.Clear();
							ep.Name = setParamName;
							ep.Value = "R";
							epl.Add(ep);
							if (!SendCommand(setCommandName, rightInstrumentName, epl, false, standardTimeout))
							{
								MessageBox.Show("ERROR: Setting" + setCommandName + " to : R.");
								pbValveLED.Image = ilLEDs.Images[5];
								status = false;
							}
							else
							{
								newStatus	= false;
							}
							break;
						case 1:
							epl.Clear();
							ep.Name = setParamName;
							ep.Value = "N";
							epl.Add(ep);
							if (!SendCommand(setCommandName, rightInstrumentName, epl, false, standardTimeout))
							{
								MessageBox.Show("ERROR: Setting" + setCommandName + " to : N.");
								pbValveLED.Image = ilLEDs.Images[5];
								status = false;
							}
							else
							{
								newStatus	= false;
							}
							break;
						case 2:
							epl.Clear();
							ep.Name = setParamName;
							ep.Value = "A";
							epl.Add(ep);
							if (!SendCommand(setCommandName, rightInstrumentName, epl, false, standardTimeout))
							{
								MessageBox.Show("ERROR: Setting" + setCommandName + " to : A.");
								pbValveLED.Image = ilLEDs.Images[5];
								status = false;
							}
							else
							{
								newStatus	= false;
							}
							break;
					}
					for (int ii = 0; ii < 1000; ii++)	//int.MaxValue / 4; ii++)
					{
						if (!newStatus)
						{
							Thread.Sleep(10);
						}
						else
						{
							newStatus	= false;

							if (!rightValveMotor)
							{
								Thread.Sleep(10);
							}
							else
							{
								break;
							}
						}
					}
					epl.Clear();

					if (!SendCommand(getCommandName, rightInstrumentName, epl, false, standardTimeout))
					{
						MessageBox.Show("ERROR: " + getCommandName);
						pbValveLED.Image = ilLEDs.Images[5];
						status = false;
					}
					Thread.Sleep(1000);
					Application.DoEvents();
				}
			}
			else if (!String.IsNullOrEmpty(rightInstrumentName) && (rightValveType == 0))
			{
				epl.Clear();

				if (!SendCommand(getCommandName, rightInstrumentName, epl, false, standardTimeout))
				{
					MessageBox.Show("ERROR: " + getCommandName);
					pbValveLED.Image = ilLEDs.Images[5];
					status = false;
				}
				Thread.Sleep(1000);
				Application.DoEvents();
			}

            #endregion

			if (status)
            {
                setLEDImages(LEDControls.ValveLED, ilLEDs.Images[3]);
            }
            this.Cursor = Cursors.Default;
        }
        /// <summary>
        /// Perform syringe test.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void buttRightsyringeTest_Click(object sender, System.EventArgs e)
        {
            if (Cursors.WaitCursor != this.Cursor)
            {
                bool status = false;
                EthernetParameterList epl = new EthernetParameterList();
                EthernetParameterList ep2 = new EthernetParameterList();
                EthernetParameter epVP = new EthernetParameter();
                EthernetParameter epVOL = new EthernetParameter();
                EthernetParameter epFR = new EthernetParameter();
                long timeout;

                try
                {
                    if (!SendCommand("Get Syringe Info", rightInstrumentName, ep2, false, standardTimeout))
                    {
                        MessageBox.Show("Error communicating with right syringe.");
                    }
					Thread.Sleep(1000);
					Application.DoEvents();

                    int heldVolume = Convert.ToInt32(tbRightHeldVolume.Text);
                    if (heldVolume > 0)
                    {
                        MessageBox.Show("Please home the instrument before running the test again.");
                        return;
                    }
                }
                catch
                {
                }
                this.Cursor = Cursors.WaitCursor;

                rightSyringeRate = "100";

                if (hashFlowRates.ContainsKey(rightSyringeSize))
				{
                    rightSyringeRate = (string)hashFlowRates[rightSyringeSize];
				}
				else
				{
					rightSyringeSize = "10000";
                    rightSyringeRate = (string)hashFlowRates[leftSyringeSize];
				}
                epl.Clear();
                epVP.Name = "Valve";
                epVP.Value = "R";
                epl.Add(epVP);

                epVOL.Name = "Volume";
                epVOL.Value = rightSyringeSize;
                epl.Add(epVOL);

                epFR.Name = "Flow Rate";
                epFR.Value = rightSyringeRate;
                epl.Add(epFR);

                timeout = long.Parse(rightSyringeSize) / long.Parse(rightSyringeRate) * 60 * 2;

                status = true;

				setLEDImages(LEDControls.RightModuleLED, ilLEDs.Images[3]);
				setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[3]);

				//-------------------------
                // Issue Aspirate commands
				//-------------------------
                for (int i = 0; i < 3; i++)
                {
                    if (!status)
                        break;
                    switch (i)
                    {
                        case 0:
                        case 2:
                            if (!SendCommand("Aspirate", rightInstrumentName, epl, false, timeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_aspirating_from_left_syringe]);
                                status = false;
                            }
							WaitForMotors((int)timeout * 2);
                            if (!SendCommand("Get Syringe Info", rightInstrumentName, ep2, false, standardTimeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                                status = false;
                            }
							Thread.Sleep(1000);
							Application.DoEvents();
                            break;
                        case 1:
                            epl["Valve"].Value = "N";
                            if (!SendCommand("Dispense", rightInstrumentName, epl, false, timeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_dispensing_from_left_syringe]);
                                status = false;
                            }
							WaitForMotors((int)timeout * 2);
                            if (!SendCommand("Get Syringe Info", rightInstrumentName, ep2, false, standardTimeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                                status = false;
                            }
							Thread.Sleep(1000);
							Application.DoEvents();
                            break;
                        default:
                            break;
                    }
                }
				setLEDImages(LEDControls.RightModuleLED, ilLEDs.Images[4]);
				setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[4]);

                if (!status)
                    setLEDImages(LEDControls.RightSyringeLED, ilLEDs.Images[5]);
                else
                    setLEDImages(LEDControls.RightSyringeLED, ilLEDs.Images[3]);

                this.Cursor = Cursors.Default;
            }
        }
        /// <summary>
        /// Perform syringe test.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void buttLeftSyringeTest_Click(object sender, System.EventArgs e)
        {
			//---------------------------------------------------------
			// If already waiting somewhere don't service button press
			//---------------------------------------------------------
            if (Cursors.WaitCursor != this.Cursor)
            {
                bool status = false;
                EthernetParameterList epl = new EthernetParameterList();
                EthernetParameterList ep2 = new EthernetParameterList();
                EthernetParameter epVP = new EthernetParameter();
                EthernetParameter epVOL = new EthernetParameter();
                EthernetParameter epFR = new EthernetParameter();
                long timeout;

                try
                {
                    if (!SendCommand("Get Syringe Info", leftInstrumentName, ep2, false, standardTimeout))
                    {
                        MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                    }
					Thread.Sleep(1000);
					Application.DoEvents();

                    int heldVolume = Convert.ToInt32(tbLeftHeldVolume.Text);
                    if (heldVolume > 0)
                    {
                        MessageBox.Show("Please home the instrument before running the test again.");
                        return;
                    }
                }
                catch
                {
                }
                this.Cursor = Cursors.WaitCursor;

                leftSyringeRate = "100";

                if (hashFlowRates.ContainsKey(leftSyringeSize))
				{
                    leftSyringeRate = (string)hashFlowRates[leftSyringeSize];
				}
				else
				{
					leftSyringeSize = "10000";
                    leftSyringeRate = (string)hashFlowRates[leftSyringeSize];
				}
                epl.Clear();
                epVP.Name = "Valve";
                epVP.Value = "R";
                epl.Add(epVP);

                epVOL.Name = "Volume";
                epVOL.Value = leftSyringeSize;
                epl.Add(epVOL);

                epFR.Name = "Flow Rate";
                epFR.Value = leftSyringeRate;
                epl.Add(epFR);

                timeout = long.Parse(leftSyringeSize) / long.Parse(leftSyringeRate) * 60 * 2;

                status = true;

				setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[3]);
				setLEDImages(LEDControls.LeftModuleLED, ilLEDs.Images[3]);

                //issue Aspirate commands
                for (int i = 0; i < 3; i++)
                {
                    if (!status)
                        break;
                    switch (i)
                    {
                        case 0:
                        case 2:
                            if (!SendCommand("Aspirate", leftInstrumentName, epl, false, timeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_aspirating_from_left_syringe]);
                                status = false;
                            }
							WaitForMotors((int)timeout * 2);
                            if (!SendCommand("Get Syringe Info", leftInstrumentName, ep2, false, standardTimeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                                status = false;
                            }
							Thread.Sleep(1000);
							Application.DoEvents();
                            break;
                        case 1:
                            epl["Valve"].Value = "N";
                            if (!SendCommand("Dispense", leftInstrumentName, epl, false, timeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_dispensing_from_left_syringe]);
                                status = false;
                            }
							WaitForMotors((int)timeout * 2);
                            if (!SendCommand("Get Syringe Info", leftInstrumentName, ep2, false, standardTimeout))
                            {
                                MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
                                status = false;
                            }
							Thread.Sleep(1000);
							Application.DoEvents();
                            break;
                        default:
                            break;
                    }
                }
				setLEDImages(LEDControls.LeftModuleLED, ilLEDs.Images[4]);
				setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[4]);

				if (!status)
					setLEDImages(LEDControls.LeftSyringeLED, ilLEDs.Images[5]);
				else
					setLEDImages(LEDControls.LeftSyringeLED, ilLEDs.Images[3]);

				this.Cursor = Cursors.Default;
            }
        }
        /// <summary>
        /// Send Zero command to device.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void buttZeroLeftSensor_Click(object sender, System.EventArgs e)
        {
            EthernetParameterList ep1 = new EthernetParameterList();
            EthernetParameterList ep2 = new EthernetParameterList();

			//---------------------------------------------------------
			// If already waiting somewhere don't service button press
			//---------------------------------------------------------
            if (Cursors.WaitCursor == this.Cursor)
			{
                return;
			}
            this.Cursor = Cursors.WaitCursor;

			ep1.Add(new EthernetParameter("Mode", ((_ZeroLeft) ? "On" : "Off"), false));

			_ZeroLeft	= !_ZeroLeft;

            if (!SendCommand("Zero Pressure", leftInstrumentName, ep1, false, standardTimeout))
            {
                MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
				setLEDImages(LEDControls.LeftSensorLED, ilLEDs.Images[5]);
            }
			else
			{
				if (!SendCommand("Get Pressure", leftInstrumentName, ep2, false, standardTimeout))
				{
					MessageBox.Show(Messages[(int)Message.Error_communicating_with_left_syringe]);
					setLEDImages(LEDControls.LeftSensorLED, ilLEDs.Images[5]);
				}
				else
				{
					if (!_ZeroLeft)
					{
						setLEDImages(LEDControls.LeftSensorLED, ilLEDs.Images[3]);
					}
					else
					{
						setLEDImages(LEDControls.LeftSensorLED, ilLEDs.Images[0]);
					}
				}
			}
			setGUI();
            this.Cursor = Cursors.Default;
        }
        /// <summary>
        /// Send Zero command to device.
        /// </summary>
        /// <param name="sender"></param>
        /// <param name="e"></param>
        private void buttZeroRightSensor_Click(object sender, System.EventArgs e)
        {
            EthernetParameterList ep1 = new EthernetParameterList();
            EthernetParameterList ep2 = new EthernetParameterList();

			//---------------------------------------------------------
			// If already waiting somewhere don't service button press
			//---------------------------------------------------------
            if (Cursors.WaitCursor == this.Cursor)
			{
                return;
			}
            this.Cursor = Cursors.WaitCursor;

			ep1.Add(new EthernetParameter("Mode", ((_ZeroRight) ? "On" : "Off"), false));

			_ZeroRight	= !_ZeroRight;

			if (!String.IsNullOrEmpty(rightInstrumentName))
			{
				if (!SendCommand("Zero Pressure", rightInstrumentName, ep1, false, standardTimeout))
				{
					MessageBox.Show(Messages[(int)Message.Error_communicating_with_right_syringe]);
					setLEDImages(LEDControls.RightSensorLED, ilLEDs.Images[5]);
				}
				else
				{
					if (!SendCommand("Get Pressure", rightInstrumentName, ep2, false, standardTimeout))
					{
						MessageBox.Show(Messages[(int)Message.Error_communicating_with_right_syringe]);
						setLEDImages(LEDControls.RightSensorLED, ilLEDs.Images[5]);
					}
					else
					{
						if (!_ZeroRight)
						{
							setLEDImages(LEDControls.RightSensorLED, ilLEDs.Images[3]);
						}
						else
						{
							setLEDImages(LEDControls.RightSensorLED, ilLEDs.Images[0]);
						}
					}
				}
			}
			setGUI();
            this.Cursor = Cursors.Default;
        }

		#endregion

		#region GUI Manipulation

		private void ClearValveVolume()
		{
		    setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[0]);
		    setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[0]);
		    setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[0]);
		    setLEDImages(LEDControls.RightValveG, ilLEDs.Images[0]);
		    setLEDImages(LEDControls.RightValveN, ilLEDs.Images[0]);
		    setLEDImages(LEDControls.RightValveR, ilLEDs.Images[0]);

			setTextBoxText(TextControls.LeftHeldVolume, "");
			setTextBoxText(TextControls.RightHeldVolume, "");
		}
		private void EnableButtons(bool _Enable)
		{
            setButtonEnabledState(ButtonControls.Home, _Enable);
            setButtonEnabledState(ButtonControls.SetSerialNumber, _Enable);
            setButtonEnabledState(ButtonControls.LeftSyringeTest, _Enable);
            setButtonEnabledState(ButtonControls.RightSyringeTest, _Enable);
            setButtonEnabledState(ButtonControls.ValveTest, _Enable);
            setButtonEnabledState(ButtonControls.ZeroLeftSensor, _Enable);
            setButtonEnabledState(ButtonControls.ZeroRightSensor, _Enable);
            setButtonEnabledState(ButtonControls.LeftButton, _Enable);
            setButtonEnabledState(ButtonControls.RightButton, _Enable);
			Application.DoEvents();
		}
		private void resetLEDsAndButtons()
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new ResetLEDsAndButtonsDelegate(resetLEDsAndButtons));
            }
            else
            {
				TestPanel.Visible	= false;

				if (statusTimer != null)
				{
					statusTimer.Enabled	= false;
				}
                buttHome.Enabled = false;
                buttLeftSyringeTest.Enabled = false;
                buttRightSyringeTest.Enabled = false;
                buttValveTest.Enabled = false;
                buttZeroLeftSensor.Enabled = false;
                buttZeroRightSensor.Enabled = false;
				//buttonReset.Enabled = false;

                tbCurrentSerialNumber.Text = "";
				//tbSerialNumber.Text = "";
                tbLeftSensorPressure.Text = "";
                tbRightSensorPressure.Text = "";
                tbLeftHeldVolume.Text = "";
                tbRightHeldVolume.Text = "";
				setLabeltext(LabelControls.LeftPressureUnits, "Bar");
				setLabeltext(LabelControls.RightPressureUnits, "Bar");
				setTextBoxText(TextControls.ErrorState, String.Empty);
				//tbSerialNumber.Focus();

                pbConnected.Image = ilLEDs.Images[0];
                pbRightSensorLED.Image = ilLEDs.Images[0];
                pbLeftSensorLED.Image = ilLEDs.Images[0];
				//pbSNLED.Image = ilLEDs.Images[0];
                pbLeftSyringeLED.Image = ilLEDs.Images[0];
                pbRightSyringeLED.Image = ilLEDs.Images[0];
                pbValveLED.Image = ilLEDs.Images[0];
                pbLFV_G.Image = ilLEDs.Images[0];
                pbLFV_N.Image = ilLEDs.Images[0];
                pbLFV_R.Image = ilLEDs.Images[0];
                pbRFV_G.Image = ilLEDs.Images[0];
                pbRFV_N.Image = ilLEDs.Images[0];
                pbRFV_R.Image = ilLEDs.Images[0];
                pbHome.Image = ilLEDs.Images[0];

				MachinePictureBox.Image		= null;
				LargeMachinePictureBox.Image= null;
				LeftValvePictureBox.Image	= null;
				RightValvePictureBox.Image	= null;

                setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[0]);
                setLEDImages(LEDControls.LeftModuleLED, ilLEDs.Images[0]);
                setLEDImages(LEDControls.RightModuleLED, ilLEDs.Images[0]);

				label7.Visible	= true;
				label8.Visible	= true;
				pbLFV_G.Visible	= true;
				pbRFV_R.Visible	= true;
				pbRFV_N.Visible	= true;
				pbRFV_G.Visible	= true;

				buttRightSyringeTest.Visible	= true;
				buttZeroRightSensor.Visible		= true;
				label2.Visible					= true;
				label4.Visible					= true;
				label8.Visible					= true;
				label9.Visible					= true;
				label10.Visible					= true;
				label12.Visible					= true;
				label14.Visible					= true;
				label18.Visible					= true;
				pbRightSyringeLED.Visible		= true;
				pbRightSensorLED.Visible		= true;
				tbRightHeldVolume.Visible		= true;
				tbRightSensorPressure.Visible	= true;

				label3.Text	= "Left " + label3.Text.Replace("Left ", String.Empty);
				label11.Text= "Left " + label11.Text.Replace("Left ", String.Empty);
				label17.Text= "Left " + label17.Text.Replace("Left ", String.Empty);

				buttLeftSyringeTest.Text	= "Left " + buttLeftSyringeTest.Text.Replace("Left ", String.Empty);
				buttZeroLeftSensor.Text		= buttZeroLeftSensor.Text.Replace("Left ", String.Empty).Replace("Zero ", "Zero Left ");

				//LeftButton.Enabled	= false;
				//RightButton.Enabled	= false;

				leftUnitID		= String.Empty;
				rightUnitID		= String.Empty;
				CheckedUnitID	= false;
            }
        }
		private void setGUI()
		{
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new VoidNoArgsDelegate(setGUI));
            }
            else
            {
				int syringeCount	= 1;

				//if (leftInstrumentName.EndsWith(" Left"))
				//{
				//	syringeCount	+= 1;
				//}
				for(int ii = 0; ii < OriginalMessages.Length && ii < Messages.Length; ii++)
				{
					Messages[ii]	= OriginalMessages[ii];
				}
				if (rightInstrumentName.EndsWith(" Right"))
				{
					syringeCount	+= 1;
				}
				//if (syringeCount == 2)
				if (syringeCount < 2)
				{
					pbRFV_R.Visible	= false;
					pbRFV_N.Visible	= false;
					pbRFV_G.Visible	= false;

					buttRightSyringeTest.Visible	= false;
					buttZeroRightSensor.Visible		= false;
					label2.Visible					= false;
					label4.Visible					= false;
					label8.Visible					= false;
					label9.Visible					= false;
					label10.Visible					= false;
					label12.Visible					= false;
					label14.Visible					= false;
					label18.Visible					= false;
					pbRightSyringeLED.Visible		= false;
					pbRightSensorLED.Visible		= false;
					tbRightHeldVolume.Visible		= false;
					tbRightSensorPressure.Visible	= false;

					label3.Text	= label3.Text.Replace("Left ", String.Empty);
					label11.Text= label11.Text.Replace("Left ", String.Empty);
					label17.Text= label17.Text.Replace("Left ", String.Empty);

					buttLeftSyringeTest.Text	= buttLeftSyringeTest.Text.Replace("Left ", String.Empty);
					buttZeroLeftSensor.Text		= buttZeroLeftSensor.Text.Replace("Left ", String.Empty);

					buttZeroLeftSensor.Text		= _ZeroLeft ? buttZeroLeftSensor.Text.Replace("Clear ", "Zero ") : buttZeroLeftSensor.Text.Replace("Zero ", "Clear ");

					for (int ii = 0; ii < Messages.Length; ii++)
					{
						Messages[ii]	= Messages[ii].Replace("left syringe", "syringe");
					}
					//MachinePictureBox.Image		= DeviceImageList.Images[0];
					LargeMachinePictureBox.Image= PumpImageList.Images[GetModelType()];
					//SingleModuleLED.Enabled	= true;
					SingleModuleLED.Visible	= true;
					LeftModuleLED.Visible	= false;
					RightModuleLED.Visible	= false;
					RightValvePictureBox.Visible	= false;

                    setLEDImages(LEDControls.SingleModuleLED, ilLEDs.Images[5]);
				}
				else
				{
					pbRFV_R.Visible	= true;
					pbRFV_N.Visible	= true;
					pbRFV_G.Visible	= true;
					pbLFV_G.Visible	= true;

					buttRightSyringeTest.Visible	= true;
					buttZeroRightSensor.Visible		= true;
					label2.Visible					= true;
					label4.Visible					= true;
					label8.Visible					= true;
					label9.Visible					= true;
					label10.Visible					= true;
					label12.Visible					= true;
					label14.Visible					= true;
					label18.Visible					= true;
					pbRightSyringeLED.Visible		= true;
					pbRightSensorLED.Visible		= true;
					tbRightHeldVolume.Visible		= true;
					tbRightSensorPressure.Visible	= true;

					label3.Text	= "Left " + label3.Text.Replace("Left ", String.Empty);
					label11.Text= "Left " + label11.Text.Replace("Left ", String.Empty);
					label17.Text= "Left " + label17.Text.Replace("Left ", String.Empty);

					buttLeftSyringeTest.Text	= "Left " + buttLeftSyringeTest.Text.Replace("Left ", String.Empty);
					buttZeroLeftSensor.Text		= buttZeroLeftSensor.Text.Replace("Left ", String.Empty).Replace("Zero ", "Zero Left ").Replace("Clear ", "Clear Left ");

					buttZeroLeftSensor.Text		= _ZeroLeft ? buttZeroLeftSensor.Text.Replace("Clear ", "Zero ") : buttZeroLeftSensor.Text.Replace("Zero ", "Clear ");
					buttZeroRightSensor.Text	= _ZeroRight ? buttZeroRightSensor.Text.Replace("Clear ", "Zero ") : buttZeroRightSensor.Text.Replace("Zero ", "Clear ");

					//MachinePictureBox.Image		= DeviceImageList.Images[1];
					LargeMachinePictureBox.Image= PumpImageList.Images[GetModelType()];
					SingleModuleLED.Visible	= false;
					LeftModuleLED.Visible	= true;
					RightModuleLED.Visible	= true;
					RightValvePictureBox.Visible	= true;

                    setLEDImages(LEDControls.LeftModuleLED, ilLEDs.Images[5]);
                    setLEDImages(LEDControls.RightModuleLED, ilLEDs.Images[5]);
				}
				if (leftValveType == 2)
				{
					label7.Visible	= false;
					pbLFV_G.Visible	= false;
					LeftValvePictureBox.Image	= DeviceImageList.Images[2];
				}
				if (rightValveType == 2)
				{
					label8.Visible	= false;
					pbRFV_G.Visible	= false;
					RightValvePictureBox.Image	= DeviceImageList.Images[2];
				}
				if (rightValveType == 0)
				{
					//label8.Visible	= false;
					//pbRFV_R.Visible	= false;
					//pbRFV_N.Visible	= false;
					//pbRFV_G.Visible	= false;
					if (syringeCount >= 2)
					{
						RightValvePictureBox.Image	= DeviceImageList.Images[4];
					}
				}
				if (leftValveType == 3)
				{
					label7.Visible	= true;
					pbLFV_G.Visible	= true;
					LeftValvePictureBox.Image	= DeviceImageList.Images[3];
				}
				if ((rightValveType == 3) &&
					(syringeCount >= 2))
				{
					label8.Visible	= true;
					pbRFV_G.Visible	= true;
					RightValvePictureBox.Image	= DeviceImageList.Images[3];
				}
				if (leftValveType == 0)
				{
					pbLFV_R.Visible	= false;
					pbLFV_N.Visible	= false;
					pbLFV_G.Visible	= false;
					label3.Visible	= false;
					label5.Visible	= false;
					label6.Visible	= false;
					label7.Visible	= false;
				}
				if (rightValveType == 0)
				{
					pbRFV_R.Visible	= false;
					pbRFV_N.Visible	= false;
					pbRFV_G.Visible	= false;
					label4.Visible	= false;
					label8.Visible	= false;
					label9.Visible	= false;
					label10.Visible	= false;
				}
				if ((rightValveType == 0) &&
					(leftValveType == 0))
				{
					buttValveTest.Visible	= false;
					pbValveLED.Visible		= false;
				}
				if (leftValveType == 2)
				{
					//LeftValvePictureBox.Location= new Point(label5.Location.X, LeftValvePictureBox.Location.Y);
					//label3.Location				= new Point(label5.Location.X - 5, label3.Location.Y);
					int l_delta		= label6.Location.X - label5.Location.X;
					int pR_delta	= pbLFV_R.Location.X - label5.Location.X;
					int pN_delta	= pbLFV_N.Location.X - label5.Location.X;
					label5.Location	= new Point(label3.Location.X + 10, label5.Location.Y);
					label6.Location	= new Point(label3.Location.X + 10 + l_delta, label6.Location.Y);
					pbLFV_R.Location= new Point(label3.Location.X + 10 + pR_delta, pbLFV_R.Location.Y);
					pbLFV_N.Location= new Point(label3.Location.X + 10 + pN_delta, pbLFV_N.Location.Y);
				}
				else
				{
					//LeftValvePictureBox.Location= new Point(label5.Location.X + 22, LeftValvePictureBox.Location.Y);
					//label3.Location				= new Point(label5.Location.X + 17, label3.Location.Y);
					int l_delta		= label6.Location.X - label5.Location.X;
					int pR_delta	= pbLFV_R.Location.X - label5.Location.X;
					int pN_delta	= pbLFV_N.Location.X - label5.Location.X;
					label5.Location	= new Point(label3.Location.X - 17, label5.Location.Y);
					label6.Location	= new Point(label3.Location.X - 17 + l_delta, label6.Location.Y);
					pbLFV_R.Location= new Point(label3.Location.X - 17 + pR_delta, pbLFV_R.Location.Y);
					pbLFV_N.Location= new Point(label3.Location.X - 17 + pN_delta, pbLFV_N.Location.Y);
				}
				if (rightValveType == 2)
				{
					//RightValvePictureBox.Location	= new Point(label10.Location.X, RightValvePictureBox.Location.Y);
					//label4.Location					= new Point(label10.Location.X - 5, label4.Location.Y);
					int l_delta		= label9.Location.X - label10.Location.X;
					int pR_delta	= pbRFV_R.Location.X - label10.Location.X;
					int pN_delta	= pbRFV_N.Location.X - label10.Location.X;
					label10.Location= new Point(label4.Location.X + 10, label10.Location.Y);
					label9.Location	= new Point(label4.Location.X + 10 + l_delta, label9.Location.Y);
					pbRFV_R.Location= new Point(label4.Location.X + 10 + pR_delta, pbRFV_R.Location.Y);
					pbRFV_N.Location= new Point(label4.Location.X + 10 + pN_delta, pbRFV_N.Location.Y);
				}
				else
				{
					//RightValvePictureBox.Location	= new Point(label10.Location.X + 22, RightValvePictureBox.Location.Y);
					//label4.Location					= new Point(label10.Location.X + 17, label4.Location.Y);
					int l_delta		= label9.Location.X - label10.Location.X;
					int pR_delta	= pbRFV_R.Location.X - label10.Location.X;
					int pN_delta	= pbRFV_N.Location.X - label10.Location.X;
					label10.Location= new Point(label4.Location.X - 17, label10.Location.Y);
					label9.Location	= new Point(label4.Location.X - 17 + l_delta, label9.Location.Y);
					pbRFV_R.Location= new Point(label4.Location.X - 17 + pR_delta, pbRFV_R.Location.Y);
					pbRFV_N.Location= new Point(label4.Location.X - 17 + pN_delta, pbRFV_N.Location.Y);
				}
				if (!pressureSensorAvailable)
				{
					buttZeroLeftSensor.Visible		= false;
					buttZeroRightSensor.Visible		= false;
					tbLeftSensorPressure.Visible	= false;
					tbRightSensorPressure.Visible	= false;
					pbLeftSensorLED.Visible			= false;
					pbRightSensorLED.Visible		= false;
					bar.Visible						= false;
					label2.Visible					= false;
					label17.Visible					= false;
					label18.Visible					= false;
				}
				else
				{
					buttZeroLeftSensor.Visible		= true;
					tbLeftSensorPressure.Visible	= true;
					pbLeftSensorLED.Visible			= true;
					bar.Visible						= true;
					label17.Visible					= true;

					if (syringeCount >= 2)
					{
						buttZeroRightSensor.Visible		= true;
						tbRightSensorPressure.Visible	= true;
						pbRightSensorLED.Visible		= true;
						label2.Visible					= true;
						label18.Visible					= true;
					}
				}
				TestPanel.Visible	= true;
			}
		}
        private void setLEDImages(LEDControls control, Image image)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new SetLEDImageDelegate(setLEDImages), new object[] { control, image });
            }
            else
            {
                switch (control)
                {
                    case LEDControls.BeaconStatus:
                        pbBeaconStatus.Image = image;
                        break;
                    case LEDControls.Connected:
                        pbConnected.Image = image;
                        break;
                    case LEDControls.Home:
                        pbHome.Image = image;
                        break;
                    case LEDControls.ValveLED:
                        pbValveLED.Image = image;
                        break;
                    case LEDControls.RightSyringeLED:
                        pbRightSyringeLED.Image = image;
                        break;
                    case LEDControls.LeftSyringeLED:
                        pbLeftSyringeLED.Image = image;
                        break;
                    case LEDControls.RightSensorLED:
                        pbRightSensorLED.Image = image;
                        break;
                    case LEDControls.LeftSensorLED:
                        pbLeftSensorLED.Image = image;
                        break;
					//case LEDControls.SerialNumber:
					//    pbSNLED.Image = image;
					//    break;
                    case LEDControls.LeftValveG:
                        pbLFV_G.Image = image;
                        break;
                    case LEDControls.LeftValveN:
                        pbLFV_N.Image = image;
                        break;
                    case LEDControls.LeftValveR:
                        pbLFV_R.Image = image;
                        break;
                    case LEDControls.RightValveG:
                        pbRFV_G.Image = image;
                        break;
                    case LEDControls.RightValveN:
                        pbRFV_N.Image = image;
                        break;
                    case LEDControls.RightValveR:
                        pbRFV_R.Image = image;
                        break;
                    case LEDControls.SingleModuleLED:
                        SingleModuleLED.Image = image;
                        break;
                    case LEDControls.LeftModuleLED:
                        LeftModuleLED.Image = image;
                        break;
                    case LEDControls.RightModuleLED:
                        RightModuleLED.Image = image;
                        break;
                    default:
                        break;
                }
            }
        }            
        private void setLabeltext(LabelControls label, string text)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new SetLabelTextDelegate(setLabeltext), new object[] { label, text });
            }
            else
            {
                switch (label)
                {
                    case LabelControls.Connect:
                        ConnectStatlbl.Text = text;
                        break;
                    case LabelControls.LeftPressureUnits:
						bar.Text	= ((text.ToUpper() == "PSI") || (text.ToUpper() == "BAR")) ? text.ToLower() : text;
                        break;
                    case LabelControls.RightPressureUnits:
						label2.Text	= ((text.ToUpper() == "PSI") || (text.ToUpper() == "BAR")) ? text.ToLower() : text;
                        break;
                    case LabelControls.ConnectedInstrumentName:
						ConnectedInstrumentName.Text	= text;
                        break;
                    case LabelControls.ConnectedInstrumentFWVersion:
						VersionInfo.Text	= text;
                        break;
                    default:
                        break;
                }
            }
        }
        private void showLabeltext(LabelControls label, bool enable)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new ShowLabelTextDelegate(showLabeltext), new object[] { label, enable });
            }
            else
            {
                switch (label)
                {
                    case LabelControls.ProgramUSBWarning:
                        ProgramQuestionLabel.Visible	= enable;
                        PowerQuestionLabel.Visible		= enable;
                        break;
                    default:
                        break;
                }
            }
        }
        private string GetTextBoxText(TextControls textBox)
        {
			string _Return	= String.Empty;

            if (this.InvokeRequired)
            {
                this.BeginInvoke(new GetTextBoxTextDelegate(GetTextBoxText), new object[] { textBox });
            }
            else
            {
                switch (textBox)
                {
                    case TextControls.CurrentSerialNumber:
						{
							_Return	= tbCurrentSerialNumber.Text;
						}
                        break;
				}
			}
			return(_Return);
		}
        private void setTextBoxText(TextControls textBox, string text)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new SetTextBoxTextDelegate(setTextBoxText), new object[] { textBox, text });
            }
            else
            {
                switch (textBox)
                {
                    case TextControls.CurrentSerialNumber:
						{
							Regex myRegex = new Regex(serialNumberFormat);
							string serialNo = text.ToUpper();

							if (myRegex.IsMatch(serialNo) && (serialNo.Length == 9))
							{
								tbCurrentSerialNumber.Text = text;
							}
						}
                        break;
                    case TextControls.ErrorState:
                        textBoxErrorState.Text = text;
                        break;
                    case TextControls.LeftHeldVolume:
                        tbLeftHeldVolume.Text = text;
                        break;
                    case TextControls.RightHeldVolume:
                        tbRightHeldVolume.Text = text;
                        break;
                    case TextControls.LeftSensorPressure:
                        tbLeftSensorPressure.Text = text;
                        break;
                    case TextControls.RightSensorPressure:
                        tbRightSensorPressure.Text = text;
                        break;
                    default:
                        break;
                }
            }
        }
        private void setButtonEnabledState(ButtonControls button, bool state)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new SetButtonEnabledStateDelegate(setButtonEnabledState), new object[] { button, state });
            }
            else
            {
                switch (button)
                {
                    case ButtonControls.Home:
                        buttHome.Enabled = state;
                        break;
					//case ButtonControls.Reset:
					//    buttonReset.Enabled = state;
					//    break;
                    case ButtonControls.ValveTest:
                        buttValveTest.Enabled = state;
                        break;
                    case ButtonControls.LeftSyringeTest:
                        buttLeftSyringeTest.Enabled = state;
                        break;
                    case ButtonControls.RightSyringeTest:
                        buttRightSyringeTest.Enabled = state;
                        break;
                    case ButtonControls.ZeroLeftSensor:
                        buttZeroLeftSensor.Enabled = state;
                        break;
                    case ButtonControls.ZeroRightSensor:
                        buttZeroRightSensor.Enabled = state;
                        break;
					//case ButtonControls.LeftButton:
					//    LeftButton.Enabled = state;
					//    break;
					//case ButtonControls.RightButton:
					//    RightButton.Enabled = state;
					//    break;
                    default:
                        break;
                }
            }
        }

		#endregion

        #region Ethernet Stuff

        /// <summary>
        /// Beacon listener.
        /// </summary>
        /// <param name="data">Instrument definitions.</param>
        private void ethernetBeaconData(EthernetReturnBase data)
        {
            if (data != null)
            {
				if ((_MACAddresses != null) && (_MACAddresses.Count <= 0))
				{
					GetMacAddress();
				}
                if (data.IP != null && data.IP.Length > 0)
                {
                    bool newInstruments = false;
					bool instrumentFound = false;
					bool _GO			= false;

					if (data.Data.Contains("<MAC>"))
					{
						string _MAC	= data.Data.Substring(data.Data.IndexOf("<MAC>") + "<MAC>".Length);
						_MAC		= _MAC.Substring(0, _MAC.IndexOf("</MAC>"));
						_MAC		= _MAC.Replace(":", "").Replace("-", "");

						if (_MACAddresses.Contains(_MAC))
						{
							_GO	= true;
						}
					}
					if (_GO)
					{
                    foreach (InstrumentDefinition dataDef in data)
                    {
						foreach (string instrumentName in instrumentsToLookFor)
						{
							if (instrumentName == dataDef.InstructionSetName)
							{
								lock(instrumentList)
								{
									foreach (InstrumentDefinition instrDef in instrumentList)
									{
										if (instrDef.Equals(dataDef))
										{
											instrumentFound = true;
											if (instrDef.Equals(connectedInstrument))
											{
												if (beaconLEDcountdown == 0)
												{
													beaconLEDcountdown = 1;
													if (beaconImageState)
													{
														setLEDImages(LEDControls.BeaconStatus, ilLEDs.Images[1]);
														beaconImageState = false;
													}
													else
													{
														setLEDImages(LEDControls.BeaconStatus, ilLEDs.Images[2]);
														beaconImageState = true;
													}
												}
												else
												{
													beaconLEDcountdown -= beaconLEDcountdown;
												}
												break;
											}
											else
											{
												MessageBox.Show("There is more than 1 instrument detected.  Using the first instrument detected", "SETUP ERROR");
											}
										}
									}
								}
								if (!instrumentFound)
								{
									dataDef.LastTimeFound = DateTime.Now;
									lock (instrumentList)
									{
										instrumentList.Add((InstrumentDefinition)dataDef);
									}
									newInstruments			= true;
									currentInstrumentName	= instrumentName;
								}
								if (newInstruments && !connectedOnLastBeacon)
								{
									setLabeltext(LabelControls.Connect, instrumentName + " Found");
									setLabeltext(LabelControls.ConnectedInstrumentName, String.Empty);
									setLabeltext(LabelControls.ConnectedInstrumentFWVersion, "Firmware Version: " + defaultFWVersion);

									connectedInstrument = dataDef;

									if (Connect())
									{
										ClearError();
										setTextBoxText(TextControls.CurrentSerialNumber, dataDef.SerialNumber);

										if (app_mode == APP_MODE.production)
										{
											if (!CheckSerialNumber(dataDef.SerialNumber))
											{
												//-------------------------------------------
												// Serial number is not compliant to format.
												//-------------------------------------------
											}
											else
											{
												setGUI();
											}
										}
										if (!statusTimer.Enabled)
										{
											statusTimer.Start();
										}
									}
									else
									{
										connectedInstrument = new InstrumentDefinition();
									}
								}
								else
								{
									//-----------------------------------------------------------------------
									// reset the beacon timer
									// so if you get a beacon every couple of seconds and
									// the timer is reset every couple of seconds then the timer never fires
									// but the beacon may not be the one your connected to so check
									//-----------------------------------------------------------------------
									beaconTimer.Enabled = false;
									beaconTimer.Enabled = true;

									setTextBoxText(TextControls.CurrentSerialNumber, dataDef.SerialNumber);
									if (tbCurrentSerialNumber.Text.Length > 0)
									{
										Regex myRegex = new Regex(serialNumberFormat);
										string serialNo = tbCurrentSerialNumber.Text.ToUpper();
										if (myRegex.IsMatch(serialNo))
										{
											//setButtonEnabledState(ButtonControls.Home, true);
											if (APP_MODE.service == app_mode)
											{
												setButtonEnabledState(ButtonControls.Reset, true);
											}
										}
										else
										{
											setButtonEnabledState(ButtonControls.Home, false);
											if (APP_MODE.service == app_mode)
											{
												setButtonEnabledState(ButtonControls.Reset, true);
											}
										}
									}
								}
								return;
							}
						}
                    }
					}
                }
            }
        }
		/// <summary>
		/// Finds the MAC address of the NIC with maximum speed.
		/// </summary>
		/// <returns>The MAC address.</returns>
		private string GetMacAddress()
		{
			const int MIN_MAC_ADDR_LENGTH = 12;
			string macAddress = string.Empty;
			long maxSpeed = -1;

			_MACAddresses.Clear();

			foreach (NetworkInterface nic in NetworkInterface.GetAllNetworkInterfaces())
			{
				Debug(
					"Found MAC Address: " + nic.GetPhysicalAddress() +
					" Type: " + nic.NetworkInterfaceType);

				string tempMac = nic.GetPhysicalAddress().ToString();

				_MACAddresses.Add(tempMac);

				if (nic.Speed > maxSpeed &&
					!string.IsNullOrEmpty(tempMac) &&
					tempMac.Length >= MIN_MAC_ADDR_LENGTH)
				{
					Debug("New Max Speed = " + nic.Speed + ", MAC: " + tempMac);
					maxSpeed = nic.Speed;
					macAddress = tempMac;
				}
			}

			return macAddress;
		}
		/// <summary>
		/// Send message to trace output.
		/// </summary>
		/// <param name="_Message">Formatted message.</param>
		private void Debug(string _Message)
		{
			System.Diagnostics.Trace.WriteLine(_Message);
		}
		/// <summary>
		/// Do we only have FTDI vid and pid?
		/// </summary>
		/// <returns>True if only FTDI</returns>
		private bool CheckForFTDIOnly()
		{
			bool _Return							= false;
			ObjectQuery _Devices					= new ObjectQuery("Select * From Win32_USBControllerDevice");
			ManagementObjectSearcher _Searcher		= new ManagementObjectSearcher(_Devices);
			ManagementObjectCollection _MyDevices	= _Searcher.Get();

			_Searcher.Dispose();

			Dictionary<string, ManagementObject> _MyListOfDevices	= new Dictionary<string, ManagementObject>();

			//SetMessageText(String.Empty);
			//SetMessageText("listenforDevicesTimer_Elapsed _MyDevices.Count : " + _MyDevices.Count + Environment.NewLine);

			//if (DebugReport) { System.Diagnostics.Trace.WriteLine("listenforDevicesTimer_Elapsed _MyDevices.Count : " + _MyDevices.Count); }

			foreach(ManagementObject _Device in _MyDevices)
			{
				string _Name	= _Device.ToString();
				int _IDIndex	= _Name.IndexOf("Win32_PnPEntity.DeviceID=");
				_IDIndex		+= "Win32_PnPEntity.DeviceID=".Length;
				int _IDEnd		= _Name.LastIndexOf("\"");
				string _ID		= _Name.Substring(_IDIndex, _IDEnd - _IDIndex);

				if (_ID.Contains("FTDIBUS"))
				{
					_ID	= _ID.Replace("A\\", "\\");
				}
				else if (_ID.Contains("USB"))
				{
					_ID	= _ID.Replace("\\\\", "&");
				}
				string _VID_PID	= _ID.Replace("\\", " ");

				if (_VID_PID.IndexOf("VID") != -1)
				{
					_VID_PID	= _VID_PID.Substring(_VID_PID.IndexOf("VID"), (_VID_PID.IndexOf(" ", _VID_PID.IndexOf("VID")) - _VID_PID.IndexOf("VID")));
					_VID_PID	= _VID_PID.Replace('&', ' ').Replace('+', ' ');
				}
				else
				{
					_VID_PID	= "No VID and PID";
				}
				if (!_MyListOfDevices.ContainsKey(_VID_PID))
				{
					if ((_VID_PID != "No VID and PID") && (_VID_PID.Split(' ').Length >= 3))
					{
						if (_VID_PID.StartsWith("VID_0403"))
						{
							_MyListOfDevices.Add(_VID_PID, _Device);
						}
					}
				}
			}
			if (_MyListOfDevices.Count > 0)
			{
				_Return	= true;
			}
			return(_Return);
		}
        /// <summary>
        /// Check for new devices added to list.
        /// </summary>
        /// <param name="sender">Who called.</param>
        /// <param name="e0">Timer arguments.</param>
        private void beaconTimer_Elapsed(object sender, System.Timers.ElapsedEventArgs e0)
        {
			if ((connectedInstrument != null) && ((connectedInstrument.InstructionSet == null) || (DateTime.Now.Subtract(connectedInstrument.LastTimeFound).TotalSeconds < 20.0)))
			{
				if ((connectedInstrument != null) && (connectedInstrument.InstructionSet == null))
				{
					if (CheckForFTDIOnly())
					{
						showLabeltext(LabelControls.ProgramUSBWarning, true);
					}
					else
					{
						showLabeltext(LabelControls.ProgramUSBWarning, false);
					}
				}
				return;
			}
			//beaconIP.Address = 0;
            setLEDImages(LEDControls.BeaconStatus, ilLEDs.Images[5]);

            foreach (GilsonTcp gtcp in socketList)
            {
                if (gtcp.IsConnected)
                {
                    gtcp.Disconnect();
                }
            }
            connectedOnLastBeacon = false;
            setLabeltext(LabelControls.Connect, "No Device Found");
			setLabeltext(LabelControls.ConnectedInstrumentName, String.Empty);
			setLabeltext(LabelControls.ConnectedInstrumentFWVersion, "Firmware Version: " + defaultFWVersion);
            currentGTCP = null;
            socketList.Clear();
            setLEDImages(LEDControls.Connected, ilLEDs.Images[0]);
            resetLEDsAndButtons();
            lock (instrumentList)
            {
                instrumentList.Clear();
            }
			if (CheckForFTDIOnly())
			{
				showLabeltext(LabelControls.ProgramUSBWarning, true);
			}
			else
			{
				showLabeltext(LabelControls.ProgramUSBWarning, false);
			}
            Application.DoEvents();
        }
		/// <summary>
        /// Get status for error and pressure if used.
		/// </summary>
        /// <param name="sender">Who called.</param>
        /// <param name="e0">Timer arguments.</param>
		private void statusTimer_Elapsed(object sender, System.Timers.ElapsedEventArgs e0)
        {
			if (statusTimer != null)
			{
				statusTimer.Enabled	= false;
			}
			try
			{
				if (connectedInstrument != null)
				{
					SendCommand("Get Error", connectedInstrument.Name, null, false, standardTimeout);

					if (connectedInstrument.InstructionSet[connectedInstrument.Name].Commands["Get Pressure"] != null)
					{
						SendCommand("Get Pressure", connectedInstrument.Name, null, false, standardTimeout);
					}
					if (!CheckedUnitID)
					{
						foreach(InstructionSetDevice _Device in connectedInstrument.InstructionSet)
						{
							if (_Device.UnitID != -1)
							{
								CheckUnitID(_Device.Name);
							}
						}
					}
				}
			}
			catch
			{
			}
			finally
			{
				statusTimer.Enabled	= true;
			}
        }
        /// <summary>
        /// Add new GilsonTcp object if available.
        /// </summary>
        /// <param name="ipAddress">IP Address</param>
        private void AddNewSocket(string ipAddress)
        {
            int port = new EthernetSend().RequestPort(ipAddress, Application.ProductName);
            if (port != -1)
            {
                GilsonTcp tcp = new GilsonTcp(System.Net.IPAddress.Parse(ipAddress), port);
                tcp.OnSocketClosed = new SocketIPDelegate(onSocketClosed);
                tcp.OnSocketConnected = new SocketIPDelegate(onSocketConnected);
                tcp.AddListener(new EthernetDataDelegate(ethernetResponseData));
                socketList.Add(tcp);
            }
        }
        /// <summary>
        /// Add new GilsonTcp object if available.
        /// </summary>
        /// <param name="ipAddress">IP Address</param>
        /// <param name="port">IP Port</param>
        /// <param name="instrumentGuid">GUID Identifier</param>
        private void AddNewSocket(string ipAddress, int port, string instrumentGuid)
        {
			if (port <= 0)
			{
				port = new EthernetSend().RequestPort(ipAddress, Application.ProductName, instrumentGuid);
			}
            if (port != -1)
			{
				GilsonTcp tcp = new GilsonTcp(System.Net.IPAddress.Parse(ipAddress), port);
				tcp.OnSocketClosed = new SocketIPDelegate(onSocketClosed);
				tcp.OnSocketConnected = new SocketIPDelegate(onSocketConnected);
				tcp.AddListener(new EthernetDataDelegate(ethernetResponseData));
				socketList.Add(tcp);
			}
        }
        /// <summary>
        /// Responses listener.
        /// </summary>
        /// <param name="data">Response to command or asynchronously pushed data.</param>
        private void ethernetResponseData(EthernetReturnBase data)
        {
            if (data.IP.Length > 0)
            {
                #region Process response Data
                if (data is EthernetResponseData)
                {
                    responseData = (EthernetResponseData)data;

					if (responseData.ResponseCodeEnum != ResponseCode.Success)
					{
                        if (responseData.ResponseValue != devicePreviousErrorCode)
                        {
                            setTextBoxText(TextControls.ErrorState, responseData.CommandName + " - " + responseData.ResponseValue);

							devicePreviousErrorCode = responseData.ResponseValue;
                        }
					}
                    switch (responseData.CommandName)
                    {
                        case "Identify":
                        case "Admin":
                            break;
                        case "Clear Error":
                            break;
                        case "Refresh Beacon":
                            break;
                        case "Get Error":
							{
								string _Message	= String.Empty;

								foreach(EthernetReturnParameter _Param in responseData.EthernetReturnParameterList)
								{
									//_Message	= _Message + "(" + _Param.ParamName + ":" + _Param.ParamValue + ") ";
									_Message	= _Message + _Param.ParamName + " : " + _Param.ParamValue + Environment.NewLine;
								}
								setTextBoxText(TextControls.ErrorState, _Message);
							}
                            break;
						case "Get Firmware Version":
							{
								if (!String.IsNullOrEmpty(responseData.ResponseValue))
								{
									currentFirmwareVersion	= responseData.ResponseValue;
								}
							}
                            break;
                        case "Get NVM":
							{
								string _Address	= String.Empty;
								string _Value	= String.Empty;

								foreach(EthernetReturnParameter _Param in responseData.EthernetReturnParameterList)
								{
									if (_Param.ParamName == "Value")
									{
										_Value	= _Param.ParamValue;
									}
								}
								//string[] response = responseData.ResponseValue.Split(new char[] { '=' });

								//  at Unit ID = 11,3=3
								
								string[] _MyValue = _Value.Split(new char[] { ',' });

								if (_MyValue.Length == 2)
								{
									string[] response = _MyValue[1].Split(new char[] { '=' });

									if (response.Length == 2)
									{
										switch (Convert.ToInt32(response[0]))
										{
											case 0:
												break;
											case 1:
												break;
											case 2:
												break;
											case 3:
												{
												if (IsInstrument(responseData, leftInstrumentName) ||
													IsInstrument(responseData, "System"))
												{
													leftValveType	= 0;

													int.TryParse(response[1], out leftValveType);

													setGUI();
												}
												else if (IsInstrument(responseData, rightInstrumentName))
												{
													rightValveType	= 0;

													int.TryParse(response[1], out rightValveType);

													setGUI();
												}
												}
												break;
											case 4:
												if (IsInstrument(responseData, leftInstrumentName) ||
													IsInstrument(responseData, "System"))
												{
													int _Test		= 0;
													leftSyringeSize	= "10000";

													if (int.TryParse(response[1], out _Test))
													{
														leftSyringeSize	= response[1];
													}
												}
												else if (IsInstrument(responseData, rightInstrumentName))
												{
													int _Test		= 0;
													rightSyringeSize= "10000";

													if (int.TryParse(response[1], out _Test))
													{
														rightSyringeSize	= response[1];
													}
												}
												break;
											case 5:
												break;
											case 6:
												break;
											case 7:
												try
												{
													int _Test	= 0;
													//leftUnitID	= "-1";
													//rightUnitID	= "-1";

													if (int.TryParse(response[1], out _Test))
													{
														if (_Test == 11)
														{
															leftUnitID	= response[1];
														}
														else if (_Test == 12)
														{
															rightUnitID	= response[1];
														}
													}
												}
												catch
												{
													leftUnitID	= "-1";
													rightUnitID	= "-1";
												}
												//if (IsInstrument(responseData, leftInstrumentName) ||
												//    IsInstrument(responseData, "System"))
												//{
												//    int _Test	= 0;
												//    leftUnitID	= "-1";

												//    if (int.TryParse(response[1], out _Test))
												//    {
												//        leftUnitID	= response[1];
												//    }
												//}
												//else if (IsInstrument(responseData, rightInstrumentName))
												//{
												//    int _Test	= 0;
												//    rightUnitID	= "-1";

												//    if (int.TryParse(response[1], out _Test))
												//    {
												//        rightUnitID	= response[1];
												//    }
												//}
												if (!String.IsNullOrEmpty(leftUnitID) && (leftUnitID != "-1") && !String.IsNullOrEmpty(rightUnitID) && (rightUnitID != "-1"))
												{
													setButtonEnabledState(ButtonControls.LeftButton, false);
													setButtonEnabledState(ButtonControls.RightButton, false);
												}
												else if (!String.IsNullOrEmpty(leftUnitID) && (leftUnitID != "-1"))
												{
													setButtonEnabledState(ButtonControls.LeftButton, false);
													setButtonEnabledState(ButtonControls.RightButton, true);
												}
												else if (!String.IsNullOrEmpty(rightUnitID) && (rightUnitID != "-1"))
												{
													setButtonEnabledState(ButtonControls.LeftButton, true);
													setButtonEnabledState(ButtonControls.RightButton, false);
												}
												CheckedUnitID	= true;

												setButtonEnabledState(ButtonControls.SetSerialNumber, true);

												CheckSerialNumber();
												break;
											case 8:
												break;
											case 9:
												break;
											case 35:
												try
												{
													int _Test			= 0;
													bool _LastZeroLeft	= _ZeroLeft;
													bool _LastZeroRight	= _ZeroRight;

													if (int.TryParse(response[1], out _Test))
													{
														if (IsInstrument(responseData, leftInstrumentName) ||
															IsInstrument(responseData, "System"))
														{
															if (_Test != 0)
															{
																_ZeroLeft	= false;
															}
															else
															{
																_ZeroLeft	= true;
															}
														}
														else if (IsInstrument(responseData, rightInstrumentName))
														{
															if (_Test != 0)
															{
																_ZeroRight	= false;
															}
															else
															{
																_ZeroRight	= true;
															}
														}
														else
														{
															if (_Test != 0)
															{
																_ZeroLeft	= false;
															}
															else
															{
																_ZeroLeft	= true;
															}
														}
													}
													else
													{
														if (IsInstrument(responseData, leftInstrumentName) ||
															IsInstrument(responseData, "System"))
														{
															_ZeroLeft	= false;
														}
														else if (IsInstrument(responseData, rightInstrumentName))
														{
															_ZeroRight	= false;
														}
														else
														{
															_ZeroLeft	= false;
														}
													}
													if ((_LastZeroLeft != _ZeroLeft) || (_LastZeroRight != _ZeroRight))
													{
														setGUI();
													}
												}
												catch
												{
													_ZeroLeft	= false;
												}
												break;
											default:
												break;
										}
									}
								}
							}
                            break;
                        case "Set NVM":
                            break;
                        case "Buffered":
                            break;
                        case "Home":
                            break;
                        case "Left Valve Position":
                            break;
                        case "Right Valve Position":
                            break;
                        case "Aspirate Right":
                            break;
                        case "Aspirate Left":
                            break;
                        case "Dispense Right":
                            break;
                        case "Dispense Left":
                            break;
						case "Get Pressure":
							{
								string _InstrumentName	= currentInstrumentName;
								int _UnitID				= 0;
								string _Units			= String.Empty;
								string _Pressure		= String.Empty;
								bool _Left				= false;
								bool _Right				= false;

								foreach (ExecutionListItem _Item in executionList)
								{
									if (_Item.SequenceNumber == responseData.SequenceNumber)
									{
										_UnitID	= _Item.UnitID;

										foreach (InstructionSetDevice _Device in connectedInstrument.InstructionSet)
										{
											if (_Device.UnitID == _UnitID)
											{
												_InstrumentName	= _Device.Name;
												break;
											}
										}
										break;
									}
								}
								if (responseData.EthernetReturnParameterList.Count == 0)
								{
									char[] _Splitter	= { '(', ')' };

									string[] _Values	= responseData.ResponseValue.Split(_Splitter, StringSplitOptions.RemoveEmptyEntries);

									if (_Values.Length >= 2)
									{
										_Pressure	= _Values[0];
										_Units		= _Values[1];
									}
								}
								else
								{
									if (responseData.EthernetReturnParameterList["Units"] != null)
									{
										_Units	= responseData.EthernetReturnParameterList["Units"].ParamValue;
									}
									if (responseData.EthernetReturnParameterList["Value"] != null)
									{
										_Pressure	= responseData.EthernetReturnParameterList["Value"].ParamValue;
									}
									if (responseData.EthernetReturnParameterList["Left"] != null)
									{
										char[] _Splitter	= { '(', ')' };
										string[] _Values	= responseData.EthernetReturnParameterList["Left"].ParamValue.Split(_Splitter, StringSplitOptions.RemoveEmptyEntries);

										if (_Values.Length >= 2)
										{
											_Left				= true;
											leftPressureReading	= _Values[0];
											_Units				= _Values[1];
										}
									}
									if (responseData.EthernetReturnParameterList["Right"] != null)
									{
										char[] _Splitter	= { '(', ')' };
										string[] _Values	= responseData.EthernetReturnParameterList["Right"].ParamValue.Split(_Splitter, StringSplitOptions.RemoveEmptyEntries);

										if (_Values.Length >= 2)
										{
											_Right				= true;
											rightPressureReading= _Values[0];
											_Units				= _Values[1];
										}
									}
								}
								if (_InstrumentName.EndsWith(" Left"))
								{
									leftPressureReading	= _Pressure;

									setLabeltext(LabelControls.LeftPressureUnits, _Units);
								}
								else if (_InstrumentName.EndsWith(" Right"))
								{
									rightPressureReading= _Pressure;

									setLabeltext(LabelControls.RightPressureUnits, _Units);
								}
								else
								{
									if (_Left || _Right)
									{
										setLabeltext(LabelControls.LeftPressureUnits, _Units);
										setLabeltext(LabelControls.RightPressureUnits, _Units);
									}
									else
									{
										leftPressureReading	= _Pressure;

										setLabeltext(LabelControls.LeftPressureUnits, _Units);
									}
								}
								setTextBoxText(TextControls.LeftSensorPressure, leftPressureReading);
								setTextBoxText(TextControls.RightSensorPressure, rightPressureReading);
							}
							break;
						case "Get Syringe Info":
							{
								string _InstrumentName	= currentInstrumentName;
								int _UnitID				= 0;
								string _ValvePosition	= String.Empty;
								string _Volume			= String.Empty;

								foreach (ExecutionListItem _Item in executionList)
								{
									if (_Item.SequenceNumber == responseData.SequenceNumber)
									{
										_UnitID	= _Item.UnitID;

										foreach (InstructionSetDevice _Device in connectedInstrument.InstructionSet)
										{
											if (_Device.UnitID == _UnitID)
											{
												_InstrumentName	= _Device.Name;
												break;
											}
										}
										break;
									}
								}
								if (responseData.EthernetReturnParameterList["Valve Position"] != null)
								{
									_ValvePosition	= responseData.EthernetReturnParameterList["Valve Position"].ParamValue;
								}
								if (responseData.EthernetReturnParameterList["Volume"] != null)
								{
									_Volume	= responseData.EthernetReturnParameterList["Volume"].ParamValue;
								}
								if (_InstrumentName.EndsWith(" Left"))
								{
									leftValvePosition	= _ValvePosition;
									leftVolumne			= _Volume;
								}
								else if (_InstrumentName.EndsWith(" Right"))
								{
									rightValvePosition	= _ValvePosition;
									rightVolumne		= _Volume;
								}
								else
								{
									leftValvePosition	= _ValvePosition;
									leftVolumne			= _Volume;
								}
								switch (leftValvePosition)
								{
									case "N":
									    setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[4]);
									    setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[0]);
									    break;
									case "R":
									    setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[4]);
									    break;
									case "A":
									    setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[4]);
									    setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[0]);
									    break;
									default:
									    break;
								}
								switch (rightValvePosition)
								{
									case "N":
									    setLEDImages(LEDControls.RightValveG, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.RightValveN, ilLEDs.Images[4]);
									    setLEDImages(LEDControls.RightValveR, ilLEDs.Images[0]);
									    break;
									case "R":
									    setLEDImages(LEDControls.RightValveG, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.RightValveN, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.RightValveR, ilLEDs.Images[4]);
									    break;
									case "A":
									    setLEDImages(LEDControls.RightValveG, ilLEDs.Images[4]);
									    setLEDImages(LEDControls.RightValveN, ilLEDs.Images[0]);
									    setLEDImages(LEDControls.RightValveR, ilLEDs.Images[0]);
									    break;
									default:
									    break;
								}
								setTextBoxText(TextControls.LeftHeldVolume, leftVolumne);
								setTextBoxText(TextControls.RightHeldVolume, rightVolumne);
							}
							break;
						case EthernetMessages.CommandGetInstructionSet:
							{
								if (responseData.EthernetReturnParameterList["Instruction Set"] != null)
								{
									InstructionSetDeviceList deviceList = new InstructionSetDeviceList();
									deviceList.ReadXml("<Gilson>" + responseData.EthernetReturnParameterList["Instruction Set"].ParamValue + "</Gilson>");

									foreach (InstrumentDefinition instrumentDef in instrumentList)
									{
										if ((responseData.InstrumentGuid != string.Empty && instrumentDef.GUID == responseData.InstrumentGuid) ||
											(responseData.InstrumentGuid == string.Empty && instrumentDef.IP == responseData.IP))
										{
											if (instrumentDef.InstructionSet == null)
											{
												instrumentDef.InstructionSet = deviceList;

												leftInstrumentName		= (instrumentDef.InstructionSet.Count > 0) ? instrumentDef.InstructionSet[0].Name : connectedInstrument.Name;	//String.Empty;
												rightInstrumentName		= String.Empty;
												pressureSensorAvailable	= false;

												foreach (InstructionSetDevice _Device in instrumentDef.InstructionSet)
												{
													if (_Device.Commands["Get Pressure"] != null)
													{
														pressureSensorAvailable	= true;
													}
													if (_Device.Name.EndsWith(" Left"))
													{
														leftInstrumentName	= _Device.Name;
													}
													else if (_Device.Name.EndsWith(" Right"))
													{
														rightInstrumentName	= _Device.Name;
													}
												}
												//if (String.IsNullOrEmpty(rightInstrumentName))
												//{
												//    label8.Enabled	= false;
												//    label9.Enabled	= false;
												//    label10.Enabled	= false;
												//    pbRFV_G.Enabled	= false;
												//    pbRFV_N.Enabled	= false;
												//    pbRFV_R.Enabled	= false;
												//}
												setGUI();
												break;
											}
										}
									}
								}
							}
							break;
                        default:
                            break;
                    }
                }
                #endregion

                #region Process Status Data
                else if ((data is EthernetStatusData) && connectedOnLastBeacon)
                {
                    statusData = (EthernetStatusData)data;

                    foreach (EthernetReturnDevice device in statusData.EthernetReturnDeviceList)
                    {
                        if (device.UnitID != connectedInstrument.UnitID)
                            return;
                        foreach (EthernetReturnCommand command in device.EthernetReturnCommandList)
                        {
                            foreach (EthernetReturnParameter parameter in command.EthernetReturnParameterList)
                            {
                                switch (parameter.ParamName)
                                {
                                    case "Error":
                                        if (parameter.ParamValue != devicePreviousErrorCode)
                                        {
                                            setTextBoxText(TextControls.ErrorState, parameter.ParamValue);
                                            if ("0 No error" != parameter.ParamValue)
                                            {
                                                //resetLEDsAndButtons();
                                                //setButtonEnabledState(ButtonControls.SetSerialNumber, true);
                                                //setButtonEnabledState(ButtonControls.Home, true);
                                                //setLEDImages(LEDControls.SerialNumber, ilLEDs.Images[3]);
                                            }
                                        }
                                        devicePreviousErrorCode = parameter.ParamValue;
                                        break;
									case "Status":
										{
											char[] _Splitter	= {':'};
											char[] _Splitter2	= {'='};
											string[] _MyStatus	= parameter.ParamValue.Split(_Splitter, StringSplitOptions.RemoveEmptyEntries);
											bool _State			= false;

											foreach(string _MotorStatus in _MyStatus)
											{
												string[] _Motor	= _MotorStatus.Split(_Splitter2, StringSplitOptions.RemoveEmptyEntries);

												if (_Motor.Length == 2)
												{
													_State	= false;

													bool.TryParse(_Motor[1], out _State);

													switch(_Motor[0])
													{
														case "ValveMotor":
														case "LeftValveMotor":
															leftValveMotor	= _State;
															break;
														case "SyringeMotor":
														case "LeftSyringeMotor":
															leftSyringeMotor	= _State;
															break;
														case "RightValveMotor":
															rightValveMotor	= _State;
															break;
														case "RightSyringeMotor":
															rightSyringeMotor	= _State;
															break;
													}
												}
											}
											newStatus	= true;
										}
                                        break;

									//case "Left Valve Position":
									//    switch (parameter.ParamValue)
									//    {
									//        case "N":
									//            setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[4]);
									//            setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[0]);
									//            break;
									//        case "R":
									//            setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[4]);
									//            break;
									//        case "G":
									//            setLEDImages(LEDControls.LeftValveG, ilLEDs.Images[4]);
									//            setLEDImages(LEDControls.LeftValveN, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.LeftValveR, ilLEDs.Images[0]);
									//            break;
									//        default:
									//            break;
									//    }
									//    leftValvePosition = parameter.ParamValue;
									//    break;
									//case "Right Valve Position":
									//    switch (parameter.ParamValue)
									//    {
									//        case "N":
									//            setLEDImages(LEDControls.RightValveG, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.RightValveN, ilLEDs.Images[4]);
									//            setLEDImages(LEDControls.RightValveR, ilLEDs.Images[0]);
									//            break;
									//        case "R":
									//            setLEDImages(LEDControls.RightValveG, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.RightValveN, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.RightValveR, ilLEDs.Images[4]);
									//            break;
									//        case "G":
									//            setLEDImages(LEDControls.RightValveG, ilLEDs.Images[4]);
									//            setLEDImages(LEDControls.RightValveN, ilLEDs.Images[0]);
									//            setLEDImages(LEDControls.RightValveR, ilLEDs.Images[0]);
									//            break;
									//        default:
									//            break;
									//    }
									//    rightValvePosition = parameter.ParamValue;
									//    break;
									//case "Left Pressure":
									//    setTextBoxText(TextControls.LeftSensorPressure, parameter.ParamValue);
									//    leftPressureReading = parameter.ParamValue;
									//    break;
									//case "Right Pressure":
									//    setTextBoxText(TextControls.RightSensorPressure, parameter.ParamValue);
									//    rightPressureReading = parameter.ParamValue;
									//    break;
									//case "Left Volume":
									//    setTextBoxText(TextControls.LeftHeldVolume, parameter.ParamValue);
									//    break;
									//case "Right Volume":
									//    setTextBoxText(TextControls.RightHeldVolume, parameter.ParamValue);
									//    break;
                                    default:
                                        break;
                                }
                            }
                        }
                    }
                }
                #endregion
            }
        }
		/// <summary>
		/// Is there a valid serial number entered?
		/// </summary>
		/// <returns>True if good format</returns>
		private bool CheckSerialNumber()
		{
			bool _Return	= false;

            if (this.InvokeRequired)
            {
                this.BeginInvoke(new BoolNoArgsDelegate(CheckSerialNumber));
            }
            else
            {
				Regex myRegex = new Regex(serialNumberFormat);
				string serialNo = tbCurrentSerialNumber.Text.ToUpper();

				if (!myRegex.IsMatch(serialNo) || (serialNo.Length != 9))
				{
					setButtonEnabledState(ButtonControls.Home, false);
				}
				else
				{
					setButtonEnabledState(ButtonControls.Home, true);
				}
            }
			return(_Return);
		}
		/// <summary>
		/// Is this a valid serial number?
		/// </summary>
		/// <param name="serialNo">Item to verify</param>
		/// <returns>True if good format</returns>
		private bool CheckSerialNumber(string serialNo)
		{
			bool _Return	= false;

            Regex myRegex = new Regex(serialNumberFormat);

            if (!myRegex.IsMatch(serialNo) || (serialNo.Length != 9))
            {
                _Return = false;
            }
			else
			{
				_Return	= true;
			}
			return(_Return);
		}
		/// <summary>
		/// Can we read NVM?
		/// </summary>
		/// <param name="_DeviceName"></param>
		/// <returns>True if check successful</returns>
		private bool CheckUnitID(string _DeviceName)
		{
			bool _Return	= false;

			_Return	= ReadNVM(_DeviceName, "7");

			return(_Return);
		}
		/// <summary>
		/// Is this instrument in response?
		/// </summary>
		/// <param name="_ResponseData">Response</param>
		/// <param name="_ThisInstrument">Instrument to look for in response.</param>
		/// <returns>True if in response.</returns>
		private bool IsInstrument(EthernetResponseData _ResponseData, string _ThisInstrument)
		{
			string _InstrumentName	= currentInstrumentName;
			int _UnitID				= 0;
			int _Count				= executionList.Count;

			//foreach (ExecutionListItem _Item in executionList)
			for(int ii = 0; ii < _Count; ii++)
			{
				ExecutionListItem _Item	= (ExecutionListItem)executionList[ii];

				if (_Item.SequenceNumber == _ResponseData.SequenceNumber)
				{
					_UnitID	= _Item.UnitID;

					foreach (InstrumentDefinition _Instrument in instrumentList)
					{
						if (_Instrument.InstructionSet != null)
						{
							foreach (InstructionSetDevice _Device in _Instrument.InstructionSet)
							{
								if (_Device.UnitID == _UnitID)
								{
									_InstrumentName	= _Device.Name;
									break;
								}
							}
							break;
						}
					}
					break;
				}
			}
			return(_InstrumentName == _ThisInstrument);
		}
        /// <summary>
        /// Socket closed event.
        /// </summary>
        /// <param name="ipAddress">IP Address</param>
        private void onSocketClosed(string ipAddress)
        {
            RemoveSocket(ipAddress);
        }
		/// <summary>
        /// Socket connected event.
		/// </summary>
        /// <param name="ipAddress">IP Address</param>
        private void onSocketConnected(string ipAddress)
        {
            try
            {
            }
            catch
            {
            }
        }
		/// <summary>
		/// Remove from socket list.
		/// </summary>
        /// <param name="ipAddress">IP Address</param>
        private void RemoveSocket(string ipAddress)
        {
            try
            {
                socketList.Remove(socketList[ipAddress]);
            }
            catch
            {
            }
        }
        /// <summary>
        /// Connect to instrument.
        /// </summary>
		/// <returns>True if successful</returns>
        private bool ConnectToInstrument()
        {
            bool status = true;

            if (socketList.Count != 0)
            {
                return false;
            }

            try
            {
                //Add IP Address to socket list
                if (instrumentList.Count > 0)
                {
                    AddNewSocket(instrumentList[0].IP, instrumentList[0].Port, instrumentList[0].GUID);
                    if (socketList.Count > 0)
                    {
                        currentGTCP = socketList[0];

                        // this seems to help connect on the first try
                        Thread.Sleep(1000);

                        if (!SendCommand("Admin", connectedInstrument.Name, null, true, standardTimeout))
                        {
                            setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
                            status = false;
                        }
                        if (!SendCommand(EthernetMessages.CommandGetInstructionSet, connectedInstrument.Name, null, true, standardTimeout))
                        {
                            setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
                            status = false;
                        }
						for (int ww = 0; ww < 1000; ww++)
						{
							Thread.Sleep(100);

							if (connectedInstrument.InstructionSet != null)
							{
								break;
							}
						}
                        if (!SendCommand(EthernetMessages.CommandGetFirmwareVersion, connectedInstrument.Name, null, true, standardTimeout))
                        {
                            setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
                            status = false;
                        }
						if (!String.IsNullOrEmpty(rightInstrumentName))
						{
							if (!ReadNVM(leftInstrumentName, "4"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
							if (!ReadNVM(rightInstrumentName, "4"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
						}
						else
						{
							if (!ReadNVM("System", "4"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
						}
						if (!String.IsNullOrEmpty(rightInstrumentName))
						{
							if (!ReadNVM(leftInstrumentName, "3"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
							if (!ReadNVM(rightInstrumentName, "3"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
						}
						else
						{
							if (!ReadNVM("System", "3"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
						}
						if (!String.IsNullOrEmpty(rightInstrumentName))
						{
							if (!ReadNVM(leftInstrumentName, "35"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
							if (!ReadNVM(rightInstrumentName, "35"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
						}
						else
						{
							if (!ReadNVM("System", "35"))
							{
								setLEDImages(LEDControls.Connected, ilLEDs.Images[5]);
								status = false;
							}
						}
                        if (!status)
                        {
                            currentGTCP = null;
                            if (socketList.Count != 0)
                            {
                                foreach (GilsonTcp gtcp in socketList)
                                {
                                    if (gtcp.IsConnected)
                                    {
                                        gtcp.Disconnect();
                                    }
                                }
                                socketList.Clear();
                            }
                        }
                        else
                        {
                            connectedOnLastBeacon = true;
                        }
                    }
					else
					{
						status = false;
					}
               }
                else
                {
                    status = false;
                }
            }
            catch (Exception e)
            {
                connectedOnLastBeacon = false;
                MessageBox.Show("Error Connecting to device : " + e.Message);
            }
            return status;
        }
        /// <summary>
        /// Clear Error(s) on all components.
        /// </summary>
		/// <returns>True if successful</returns>
        private bool ClearError()
        {
            return SendCommand("Clear Error", connectedInstrument.Name, null, false, standardTimeout);
        }
		/// <summary>
		/// Set instrument NVRAM.
		/// </summary>
		/// <param name="InstrumentName">Instrument Name</param>
		/// <param name="address">NVRAM address</param>
		/// <param name="val">Value</param>
		/// <returns>True if successful</returns>
		private bool SetNVM(string InstrumentName, string address, string val)
        {
            EthernetParameterList epl	= new EthernetParameterList();
            EthernetParameter ep1		= new EthernetParameter("Address", address);

            epl.Add(ep1);

            EthernetParameter ep2 = new EthernetParameter("Value", val);

            epl.Add(ep2);

            return SendCommand("Set NVM", InstrumentName, epl, (((connectedInstrument.InstructionSet[InstrumentName].Commands["Set NVM"] != null) && (InstrumentName != "System")) ? false : true), 3000L);
        }
		/// <summary>
		/// Read instrument NVRAM.
		/// Function does not block but process response in ethernet listener.
		/// </summary>
		/// <param name="InstrumentName">Instrument Name</param>
		/// <param name="address">NVRAM address</param>
		/// <returns>True if successful</returns>
        private bool ReadNVM(string InstrumentName, string address)
        {
            EthernetParameterList epl	= new EthernetParameterList();
            EthernetParameter epAddress = new EthernetParameter("Address", address);

            epl.Add(epAddress);

			return SendCommand("Get NVM", InstrumentName, epl, ((InstrumentName != "System") && ((connectedInstrument.InstructionSet != null) && (connectedInstrument.InstructionSet[InstrumentName].Commands["Get NVM"] != null)) ? false : true), standardTimeout);
		}
        /// <summary>
        /// Sends either a command to an Ethernet or GSIOC conented device.
        /// </summary>
        /// <param name="Command">Command name</param>
		/// <param name="InstrumentName">Instrument Name</param>
        /// <param name="epl">EthernetParameterList</param>
        /// <param name="SystemCommand">true if a "sys" command, other wise the instrument type</param>
		/// <param name="timeout">Time out</param>
		/// <returns>True if successful</returns>
        private bool SendCommand(string Command, string InstrumentName, EthernetParameterList epl, bool SystemCommand, long timeout)
        {
            bool retval = false;

			lock(SendLock)
			{
				string commandTarget = SystemCommand ? "System" : InstrumentName;
				int _UnitID	= connectedInstrument.UnitID;

				foreach (InstrumentDefinition _Instrument in instrumentList)
				{
					if (_Instrument.InstructionSet != null)
					{
						foreach (InstructionSetDevice _Device in _Instrument.InstructionSet)
						{
							if (_Device.Name == InstrumentName)
							{
								_UnitID	= _Device.UnitID;
								break;
							}
						}
					}
				}
				EthernetResponseData erb = null;
				EthernetMessage em	= new EthernetMessage();
				EthernetCommand ec	= new EthernetCommand(Command, commandTarget, _UnitID, true);
				ec.SequenceNumber	= sequenceNumber;
				sequenceNumber		+= 1;

				if (null != epl)
				{
					foreach (EthernetParameter ep in epl)
					{
						ec.Parameters.Add(ep);
					}
				}
				em.Commands.Add(ec);

				if (currentGTCP != null)
					executionList.Add(new ExecutionListItem(currentGTCP.IPAddress, currentGTCP.Port, ec.UnitID, ec.SequenceNumber));

				if (currentGTCP != null)
					erb = (EthernetResponseData)currentGTCP.TcpSendAndWait(em, timeout);
				if (null != erb)
				{
					ethernetResponseData(erb);
					retval = true;
				}
			}
            return retval;
        }
        #endregion

    }
}
