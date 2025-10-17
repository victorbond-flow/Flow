def go_to(vial_number, rack_commands, session):
    """
    Move the Gilson arm to the given vial number.

    Parameters:
    -----------
    vial_number : int
        The vial number to go to
    rack_commands : Rackcommands object
        Used to translate vial_number to XY coordinates
    session : GilsonSession object
        Used to send movement commands to the liquid handler
    """
    #Get XY command from rack
    coords = rack_commands.get_xy_command(vial_number)
    
    #Extract numeric X and Y values
    x_str, y_str = coords[0].split('/')
    x_val = float(x_str[1:])
    y_val = float(y_str[1:])
    
    # 3. Send commands to the hardware
    # For software-only testing, replace the next two lines with print()
    print(f"Moving to X={x_val}, Y={y_val}")
    #session.move_x(x_val)
    #session.move_y(y_val)