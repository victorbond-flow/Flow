using System;
using System.Drawing;
using System.Collections;
using System.ComponentModel;
using System.Windows.Forms;

namespace Verity4000SeriesExampleGEARS
{
	/// <summary>
	/// Summary description for About.
	/// </summary>
	public class About : System.Windows.Forms.Form
	{
		private System.Windows.Forms.Label productLbl;
		private System.Windows.Forms.Label copyrightLbl;
		private System.Windows.Forms.Label versionLbl;
		private System.Windows.Forms.Button okBtn;
		private System.Windows.Forms.PictureBox pictureBox1;
		/// <summary>
		/// Required designer variable.
		/// </summary>
		private System.ComponentModel.Container components = null;
		/// <summary>
		/// About constructor.
		/// Sets version text.
		/// </summary>
		public About()
		{
			//
			// Required for Windows Form Designer support
			//
			InitializeComponent();

			versionLbl.Text = "Version: " + Application.ProductVersion;
		}
		/// <summary>
		/// Clean up any resources being used.
		/// </summary>
		protected override void Dispose( bool disposing )
		{
			if( disposing )
			{
				if(components != null)
				{
					components.Dispose();
				}
			}
			base.Dispose( disposing );
		}

		#region Windows Form Designer generated code
		/// <summary>
		/// Required method for Designer support - do not modify
		/// the contents of this method with the code editor.
		/// </summary>
		private void InitializeComponent()
		{
			System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(About));
			this.productLbl = new System.Windows.Forms.Label();
			this.copyrightLbl = new System.Windows.Forms.Label();
			this.versionLbl = new System.Windows.Forms.Label();
			this.okBtn = new System.Windows.Forms.Button();
			this.pictureBox1 = new System.Windows.Forms.PictureBox();
			((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).BeginInit();
			this.SuspendLayout();
			// 
			// productLbl
			// 
			this.productLbl.Location = new System.Drawing.Point(40, 128);
			this.productLbl.Name = "productLbl";
			this.productLbl.Size = new System.Drawing.Size(224, 24);
			this.productLbl.TabIndex = 0;
			this.productLbl.Text = "Verity 4000 Series Example GEARS";
			this.productLbl.TextAlign = System.Drawing.ContentAlignment.TopCenter;
			// 
			// copyrightLbl
			// 
			this.copyrightLbl.Location = new System.Drawing.Point(40, 200);
			this.copyrightLbl.Name = "copyrightLbl";
			this.copyrightLbl.Size = new System.Drawing.Size(232, 24);
			this.copyrightLbl.TabIndex = 1;
			this.copyrightLbl.Text = "Copyright 2015 Gilson, Inc.";
			this.copyrightLbl.TextAlign = System.Drawing.ContentAlignment.TopCenter;
			// 
			// versionLbl
			// 
			this.versionLbl.Location = new System.Drawing.Point(35, 152);
			this.versionLbl.Name = "versionLbl";
			this.versionLbl.Size = new System.Drawing.Size(224, 24);
			this.versionLbl.TabIndex = 2;
			this.versionLbl.Text = "Version";
			this.versionLbl.TextAlign = System.Drawing.ContentAlignment.TopCenter;
			// 
			// okBtn
			// 
			this.okBtn.DialogResult = System.Windows.Forms.DialogResult.OK;
			this.okBtn.Location = new System.Drawing.Point(120, 256);
			this.okBtn.Name = "okBtn";
			this.okBtn.Size = new System.Drawing.Size(75, 23);
			this.okBtn.TabIndex = 3;
			this.okBtn.Text = "&OK";
			// 
			// pictureBox1
			// 
			this.pictureBox1.Dock = System.Windows.Forms.DockStyle.Top;
			this.pictureBox1.Image = ((System.Drawing.Image)(resources.GetObject("pictureBox1.Image")));
			this.pictureBox1.Location = new System.Drawing.Point(0, 0);
			this.pictureBox1.Name = "pictureBox1";
			this.pictureBox1.Size = new System.Drawing.Size(306, 88);
			this.pictureBox1.TabIndex = 4;
			this.pictureBox1.TabStop = false;
			// 
			// About
			// 
			this.AutoScaleBaseSize = new System.Drawing.Size(5, 14);
			this.ClientSize = new System.Drawing.Size(306, 286);
			this.Controls.Add(this.pictureBox1);
			this.Controls.Add(this.okBtn);
			this.Controls.Add(this.versionLbl);
			this.Controls.Add(this.copyrightLbl);
			this.Controls.Add(this.productLbl);
			this.Font = new System.Drawing.Font("Tahoma", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
			this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog;
			this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
			this.MaximizeBox = false;
			this.MinimizeBox = false;
			this.Name = "About";
			this.ShowInTaskbar = false;
			this.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent;
			this.Text = "About";
			((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).EndInit();
			this.ResumeLayout(false);

		}
		#endregion
	}
}
