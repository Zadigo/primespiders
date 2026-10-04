from __future__ import annotations

from abc import ABC, abstractmethod


class Component(ABC):
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    @property
    def parent(self) -> Component:
        return self._parent

    @parent.setter
    def parent(self, parent: Component):
        self._parent = parent

    @abstractmethod
    def operation(self) -> str:
       pass

    def add(self, component: Component) -> None:
        pass

    def remove(self, component: Component) -> None:
        pass

    def is_composite(self) -> bool:
        return False



class Leaf(Component):
    def operation(self) -> str:
        return "Leaf"


class Composite(Component):
    def __init__(self) -> None:
        self._children: list[Component] = []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._children}>"

    def add(self, component: Component) -> None:
        self._children.append(component)
        component.parent = self

    def remove(self, component: Component) -> None:
        self._children.remove(component)
        component.parent = None

    def is_composite(self) -> bool:
        return True

    def operation(self) -> str:
        results = []
        for child in self._children:
            results.append(child.operation())
        return f"Branch({'+'.join(results)})"


tree = Composite()

branch = Composite()
branch.add(Leaf())
branch.add(Leaf())

tree.add(branch)

print(tree)
print(tree.operation())

# def client_code(component: Component) -> None:
#     print(f"RESULT: {component.operation()}", end="")


# def client_code2(component1: Component, component2: Component) -> None:
#     if component1.is_composite():
#         component1.add(component2)

#     print(f"RESULT: {component1.operation()}", end="")


# if __name__ == "__main__":
#     simple = Leaf()
#     print("Client: I've got a simple component:")
#     client_code(simple)

#     print("\n")

#     # ...as well as the complex composites.
#     tree = Composite()

#     branch1 = Composite()
#     branch1.add(Leaf())
#     branch1.add(Leaf())

#     branch2 = Composite()
#     branch2.add(Leaf())

#     tree.add(branch1)
#     tree.add(branch2)

#     print("Client: Now I've got a composite tree:")
#     client_code(tree)
#     print("\n")

#     print("Client: I don't need to check the components classes even when managing the tree:")
#     client_code2(tree, simple)
