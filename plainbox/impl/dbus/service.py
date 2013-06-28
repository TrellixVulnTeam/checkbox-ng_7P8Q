# This file is part of Checkbox.
#
# Copyright 2013 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# Checkbox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Checkbox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Checkbox.  If not, see <http://www.gnu.org/licenses/>.

"""
:mod:`plainbox.impl.dbus.service` -- DBus Service support code for PlainBox
===========================================================================
"""

import logging

import _dbus_bindings
import dbus
import dbus.service
import dbus.exceptions

from dbus.service import method, signal

__all__ = ['signal', 'method', 'property', 'Object', 'Interface']

logger = logging.getLogger("plainbox.dbus")


class InterfaceType(dbus.service.InterfaceType):
    """
    Subclass of :class:`dbus.service.InterfaceType` that also handles
    properties.
    """

    def _reflect_on_property(cls, func):
        reflection_data = (
            '    <property name="{}" type="{}" access="{}"/>\n').format(
                func._dbus_property, func._signature,
                func.dbus_access_flag)
        return reflection_data


#Subclass of :class:`dbus.service.Interface` that also handles properties
Interface = InterfaceType('Interface', (dbus.service.Interface,), {})


class property:
    """
    property that handles DBus stuff
    """

    def __init__(self, signature, dbus_interface, dbus_property=None,
                 setter=False):
        """
        Initialize new dbus_property with the given interface name.

        If dbus_property is not specified it is set to the name of the
        decorated method. In special circumstances you may wish to specify
        alternate dbus property name explicitly.

        If setter is set to True then the implicit decorated function is a
        setter, not the default getter. This allows to define write-only
        properties.
        """
        self.__name__ = None
        self.__doc__ = None
        self._signature = signature
        self._dbus_interface = dbus_interface
        self._dbus_property = dbus_property
        self._getf = None
        self._setf = None
        self._implicit_setter = setter

    @property
    def dbus_access_flag(self):
        """
        access flag of this DBus property

        :returns: either "readwrite", "read" or "write"
        :raises TypeError: if the property is ill-defined
        """
        if self._getf and self._setf:
            return "readwrite"
        elif self._getf:
            return "read"
        elif self._setf:
            return "write"
        else:
            raise TypeError(
                "property provides neither readable nor writable")

    @property
    def dbus_interface(self):
        """
        name of the DBus interface of this DBus property
        """
        return self._dbus_interface

    @property
    def dbus_property(self):
        """
        name of this DBus property
        """
        return self._dbus_property

    @property
    def signature(self):
        """
        signature of this DBus property
        """
        return self._signature

    @property
    def setter(self):
        """
        decorator for setter functions

        This property can be used to decorate additional method that
        will be used as a property setter. Otherwise properties cannot
        be assigned.
        """
        def decorator(func):
            self._setf = func
            return self
        return decorator

    @property
    def getter(self):
        """
        decorator for getter functions

        This property can be used to decorate additional method that
        will be used as a property getter. It is only provider for parity
        as by default, the @dbus.service.property() decorator designates
        a getter function. This behavior can be controlled by passing
        setter=True to the property initializer.
        """
        def decorator(func):
            self._getf = func
            return self
        return decorator

    def __call__(self, func):
        """
        Decorate a getter function and return the property object

        This method sets __name__, __doc__ and _dbus_property.
        """
        self.__name__ = func.__name__
        if self.__doc__ is None:
            self.__doc__ = func.__doc__
        if self._dbus_property is None:
            self._dbus_property = func.__name__
        if self._implicit_setter:
            return self.setter(func)
        else:
            return self.getter(func)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            if self._getf is None:
                raise dbus.exceptions.DBusException(
                    "property is not readable")
            return self._getf(instance)

    def __set__(self, instance, value):
        if self._setf is None:
            raise dbus.exceptions.DBusException(
                "property is not writable")
        self._setf(instance, value)

    # This little helper is here is to help :meth:`Object.Introspect()`
    # figure out how to handle properties.
    _dbus_is_property = True


class Object(Interface, dbus.service.Object):
    """
    dbus.service.Object subclass that provides DBus properties interface.

    Implements Get(), Set() and GetAll(). Every actual property needs to
    be implemented with the @dbus_property decorator.

    This class also overrides Introspect() from the
    org.freedesktop.DBus.Introspectable interface so that all of the
    properties are properly accounted for.
    """

    @method(
        dbus_interface=dbus.INTROSPECTABLE_IFACE,
        in_signature='', out_signature='s',
        path_keyword='object_path', connection_keyword='connection')
    def Introspect(self, object_path, connection):
        """
        Return a string of XML encoding this object's supported interfaces,
        methods and signals.
        """
        logger.debug("Introspect(object_path=%r)", object_path)
        reflection_data = (
            _dbus_bindings.DBUS_INTROSPECT_1_0_XML_DOCTYPE_DECL_NODE)
        reflection_data += '<node name="%s">\n' % object_path
        interfaces = self._dbus_class_table[
            self.__class__.__module__ + '.' + self.__class__.__name__]
        for (name, funcs) in interfaces.items():
            reflection_data += '  <interface name="%s">\n' % (name)
            for func in funcs.values():
                if getattr(func, '_dbus_is_method', False):
                    reflection_data += self.__class__._reflect_on_method(func)
                elif getattr(func, '_dbus_is_signal', False):
                    reflection_data += self.__class__._reflect_on_signal(func)
                elif getattr(func, '_dbus_is_property', False):
                    reflection_data += (
                        self.__class__._reflect_on_property(func))
            reflection_data += '  </interface>\n'
        for name in connection.list_exported_child_objects(object_path):
            reflection_data += '  <node name="%s"/>\n' % name
        reflection_data += '</node>\n'
        logger.debug("Introspect() returns: %s", reflection_data)
        return reflection_data

    @dbus.service.method(
        dbus_interface=dbus.PROPERTIES_IFACE,
        in_signature="ss", out_signature="v")
    def Get(self, interface_name, property_name):
        """
        Get the value of a property @property_name on interface
        @interface_name.
        """
        logger.debug("Get(%r, %r)", interface_name, property_name)
        property_iface_map = self._get_property_iface_map()
        if interface_name not in property_iface_map:
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "No such interface {}".format(interface_name))
        if property_name not in property_iface_map[interface_name]:
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "No such property {}:{}".format(
                    interface_name, property_name))
        name = property_iface_map[interface_name][property_name]
        try:
            return getattr(self, name)
        except dbus.exceptions.DBusException:
            raise
        except Exception as exc:
            logger.exception(
                "runaway exception from Get(%r, %r)",
                interface_name, property_name)
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "Unable to get property interface/property {}:{}: {!r}".format(
                    interface_name, property_name, exc))

    @dbus.service.method(
        dbus_interface=dbus.PROPERTIES_IFACE,
        in_signature="ssv", out_signature="")
    def Set(self, interface_name, property_name, value):
        logger.debug("Set(%r, %r, %r)", interface_name, property_name, value)
        property_iface_map = self._get_property_iface_map()
        if interface_name not in property_iface_map:
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "No such interface {}".format(interface_name))
        if property_name not in property_iface_map[interface_name]:
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "No such property {}:{}".format(
                    interface_name, property_name))
        name = property_iface_map[interface_name][property_name]
        try:
            setattr(self, name, value)
        except dbus.exceptions.DBusException:
            raise
        except Exception as exc:
            logger.exception(
                "runaway exception from Set(%r, %r, %r)",
                interface_name, property_name, value)
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "Unable to set property {}:{}: {!r}".format(
                    interface_name, property_name, exc))

    @dbus.service.method(
        dbus_interface=dbus.PROPERTIES_IFACE,
        in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface_name):
        logger.debug("GetAll(%r)", interface_name)
        property_iface_map = self._get_property_iface_map()
        if interface_name not in property_iface_map:
            raise dbus.exceptions.DBusException(
                dbus.PROPERTIES_IFACE,
                "No such interface {}".format(interface_name))
        else:
            return {
                property_name: self.Get(interface_name, property_name)
                for property_name in property_iface_map[interface_name]
            }

    @dbus.service.signal(
        dbus_interface=dbus.PROPERTIES_IFACE,
        signature='sa{sv}as')
    def PropertiesChanged(
            self, interface_name, changed_properties, invalidated_properties):
        logger.debug(
            "PropertiesChanged(%r, %r, %r)",
            interface_name, changed_properties, invalidated_properties)

    # None helper that is overriden per-class in _get_property_iface_map()
    _property_iface_map = None

    @classmethod
    def _get_property_iface_map(cls):
        """
        Get or construct (once) property-interface map out of methods
        decorated with @dbus_property decorator.
        """
        if cls._property_iface_map is None:
            property_iface_map = cls._build_property_iface_map()
            logger.debug("built property_iface_map: %r", property_iface_map)
            cls._property_iface_map = property_iface_map
        return cls._property_iface_map

    @classmethod
    def _build_property_iface_map(cls):
        """
        Construct property-interface map out of methods
        decorated with @dbus_property decorator.
        """
        pif = {}  # property_iface_map
        logger.debug("Looking for dbus_property instances in %r", cls)
        for name in dir(cls):
            obj = cls.__dict__.get(name)
            if not isinstance(obj, property):
                continue
            logger.debug("Found DBus property %r", obj)
            if obj._dbus_interface not in pif:
                pif[obj._dbus_interface] = {}
            pif[obj._dbus_interface][obj._dbus_property] = name
        return pif
