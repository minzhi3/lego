from lego_factory import LegoFactory
import ocp_vscode


factory = LegoFactory()
result = factory.make_rectangle(2, 4, 4)

ocp_vscode.show_object(result, clear=True)
