include("$(PORT_DIR)/boards/manifest.py")
package("microdot", base_path="src")
package("umsgpack", base_path="src")
module("bme280_float.py", base_path="src")

