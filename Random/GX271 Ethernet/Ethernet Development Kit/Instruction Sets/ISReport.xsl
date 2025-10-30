<?xsl version="1.0" ?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:template match="/">
		<HTML>
			<HEAD>
				<TITLE>Instruction Set Command Report</TITLE>
			</HEAD>
			<BODY>
				<font face="Verdana">
					<table width="100%" border="2" cellpadding="3" cellspacing="0">
						<tr bgColor="gainsboro">
							<td align="center" colspan="2">
								<font size="4" face="Verdana">
									<b>Instruction Set Command Report</b>
								</font>
							</td>
						</tr>
					</table>
					<br/>
					
					<table border="0" cellpadding="1" cellspacing="2" width="100%">
						
						<xsl:for-each select="Gilson/InstructionSet/Devices/Device">
														
									<tr>
										<td bgcolor="#cccccc" valign="top" width="30%">
											<h2>Device Name</h2>
										</td>
									
										<td bgcolor="#cccccc" valign="top" width="70%">
											<h2><xsl:value-of select="DeviceName"/></h2>
										</td>
									</tr>
									<tr>
										<td bgcolor="#cccccc" valign="top">
											Version
										</td>
									
										<td bgcolor="#cccccc" valign="top">
											<xsl:value-of select="DeviceVersion"/>
										</td>
									</tr>
									<tr>
										<td bgcolor="#cccccc" valign="top">
											Unit ID
										</td>
									
										<td bgcolor="#cccccc" valign="top">
											<xsl:value-of select="DeviceId"/>
										</td>
									</tr>
									
									<!-- Add status information -->
									<xsl:if test="./StatusDefinition">
										<tr>
											<td colspan="2">
												<table border="1" cellpadding="1" cellspacing="2" width="100%">
													<tr>
														<td bgcolor="gainsboro" valign="top">
															<strong>Status Command</strong>
														</td>
														<td bgcolor="gainsboro" valign="top">
															<strong>Frequency</strong>
														</td>
													</tr>
													<xsl:for-each select="./StatusDefinition/StatusCommands/StatusCommand">
														<tr>
															<td bgcolor="white" valign="top">
																<small><xsl:value-of select="CommandName"/></small>
															</td>
																<xsl:choose>
																	<xsl:when test="PollingCommand = 0">
																		<td bgcolor="white" valign="top">
																			<small>Sent once per command</small>
																		</td>
																	</xsl:when>
																	<xsl:otherwise>
																		<td bgcolor="white" valign="top">
																			<small>Always on</small>
																		</td>
																	</xsl:otherwise>
																</xsl:choose>
														</tr>
													</xsl:for-each>
												</table>
											</td>
										</tr>
									</xsl:if>
									
									<!-- Add data collection information -->
									<xsl:if test="./DataDefinition">
										<tr>
											<td colspan="2">
												<table border="1" cellpadding="1" cellspacing="2" width="100%">
													<xsl:if test="./DataDefinition/EventQueueCommand">
														<tr>
															<td bgcolor="white" valign="top">
																<small>Event Queue Command</small>
															</td>
															<td bgcolor="white" valign="top">
																<small><xsl:value-of select="./DataDefinition/EventQueueCommand/CommandName"/></small>
															</td>
														</tr>
													</xsl:if>
													
													<tr>
														<td bgcolor="gainsboro" valign="top">
															<strong>Data Command</strong>
														</td>
														<td bgcolor="gainsboro" valign="top">
															<strong>Data Channel</strong>
														</td>
													</tr>

													<xsl:for-each select="./DataDefinition/DataCommand">
														<tr>
															<td bgcolor="white" valign="top">
																<small><xsl:value-of select="CommandName"/></small>
															</td>
															<td bgcolor="white" valign="top">
																<small><xsl:value-of select="Channel"/></small>
															</td>
														</tr>
													</xsl:for-each>
												</table>
											</td>
										</tr>
									</xsl:if>
									
									<tr>
										<td colspan="2">
											<table border="1" cellpadding="1" cellspacing="2" width="100%">
												<tr>
												
																<td bgcolor="gainsboro" valign="top">
																	<strong>Command Name</strong>
																</td>
																<td bgcolor="gainsboro" valign="top">
																	<strong>Notes</strong>
																</td>
																<td bgcolor="gainsboro" valign="top">
																	<strong>Parameters</strong>
																</td>
																
												</tr>
												
												
												<xsl:for-each select="./CommandDefinitions/CommandDefinition">
																				
															<tr>
															
																<td bgcolor="white" valign="top">
																	<xsl:value-of select="CommandName"/>
																</td>
																<td bgcolor="white" valign="top">
																	<small><xsl:value-of select="CommandNotes"/></small>
																</td>
																		<td>
																			<table border="0" cellpadding="1" cellspacing="2" width="100%">
																				<xsl:if test="./Parameters">
																					<tr>
																									<td width="30%"  bgcolor="lightblue" valign="top">
																										<small><u>Name</u></small>
																									</td>
																									<td width="15%" bgcolor="lightblue" valign="top">
																										<small><u>Type</u></small>
																									</td>
																									<td width="10%" bgcolor="lightblue" valign="top">
																										<small><u>Default</u></small>
																									</td>
																									<td width="10%" bgcolor="lightblue" valign="top">
																										<small><u>Units</u></small>
																									</td>
																									<td width="10%" bgcolor="lightblue" valign="top">
																										<small><u>Range</u></small>
																									</td>
																									<td width="25%" bgcolor="lightblue" valign="top">
																										<small><u>Notes</u></small>
																									</td>
																					</tr>
																					<xsl:for-each select="./Parameters/Parameter">
																												
																						<tr>
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterName"/></small>
																							</td>
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterType"/></small>
																							</td>	
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterDefault"/></small>
																							</td>	
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterUnits"/></small>
																							</td>	
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="RangeInfo/Min"/> - <xsl:value-of select="RangeInfo/Max"/></small>
																							</td>	
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterNotes"/></small>
																							</td>
																						</tr>			
																					</xsl:for-each>
																				</xsl:if>
																				
																				<xsl:if test="./ReturnParameters">
																					<tr>
																									<td width="30%"  bgcolor="salmon" valign="top">
																										<small><u>Name</u></small>
																									</td>
																									<td width="15%" bgcolor="salmon" valign="top">
																										<small><u>Type</u></small>
																									</td>
																									<td width="25%" bgcolor="salmon" valign="top" colspan="4">
																										<small><u>Notes</u></small>
																									</td>
																					</tr>
																					<xsl:for-each select="./ReturnParameters/ReturnParameter">
																														
																						<tr>
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterName"/></small>
																							</td>
																							<td bgcolor="white" valign="top">
																								<small><xsl:value-of select="ParameterType"/></small>
																							</td>	
																							<td bgcolor="white" valign="top" colspan="4">
																								<small><xsl:value-of select="ParameterNotes"/></small>
																							</td>
																						</tr>			
																					</xsl:for-each>
																				</xsl:if>
																				
																					<xsl:if test="./MotionCommands">
																					<tr>
																						<td width="30%"  bgcolor="moccasin" valign="top" colspan="6">
																							<small><u>Name</u></small>
																						</td>
																					</tr>
																					<xsl:for-each select="./MotionCommands/CommandName">
																														
																						<tr>
																							<td bgcolor="white" valign="top" colspan="6">
																								<small><xsl:value-of select="."/></small>
																							</td>
																						</tr>			
																					</xsl:for-each>
																				</xsl:if>
		
																			</table>
																		</td>
																</tr>			
												</xsl:for-each>
												
											</table>
										</td>
									</tr>									
						</xsl:for-each>
					</table>
					<br/>
					<small><small>Gilson Inc.</small></small>
				</font>
			</BODY>
		</HTML>
	</xsl:template>
</xsl:stylesheet>
