from lego_factory import LegoFactory
import ocp_vscode


factory = LegoFactory()
result = factory.make_slope(2, 4, 2, 4, "sine")

ocp_vscode.show(result)
