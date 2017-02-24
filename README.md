# pyLaser
###### By AppliedEllipsis
Python Interface for  HTPOW (Cheap Chinese CNC Laser Engravers)

**[Todo](https://github.com/AppliedEllipsis/pyLaser/blob/master/Todo.md)**

**[License](https://github.com/AppliedEllipsis/pyLaser/blob/master/LICENSE.txt)**

**[Source](https://github.com/AppliedEllipsis/pyLaser/blob/master/pyLaser.py)**

**Hardware**
* The laser this is developed against is a cheap sub-$100 cnc 1000mw laser from China.
 * The laser enclosure is unbranded
 * It is listed as HW V2, Firmware V2.4
 * The software it uses is HTOPW.
  * I am not a big fan of this software as it seems to only do raster stuff, and isn't the most user friendly, but it is functional.
  * It also goes by the name of SuperCarver (software and laser engraver)
 * It looks identical to some cheap chinese NEJE Lasers, but the protocol seems to be different
 * Mine came with a bad power supply and EU converter, so I just use a USB power cable and connect it to a 2.4amp power source or powerbank (not very stable, as it seems to go into standby mode with the power bank)

![Image of Cheap Chinese Laser](https://github.com/AppliedEllipsis/pyLaser/raw/master/laser_cutter.jpg)
