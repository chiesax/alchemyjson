from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey, Column
from sqlalchemy.sql.sqltypes import Integer, String

__author__ = 'chiesa'

BASE = declarative_base()


class Managers(BASE):

    __tablename__ = 'managers'

    id = Column(Integer, primary_key=True)
    name = Column(String)

class Employees(BASE):

    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    manager_id = Column(Integer, ForeignKey('managers.id'))

    manager = relationship(Managers, backref='employees')


