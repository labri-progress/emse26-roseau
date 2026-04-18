package genericsClazzMethodTypeBoundsSpecialization;

import testing_lib.genericsClazzMethodTypeBoundsSpecialization.GenericsClazzMethodTypeBoundsSpecialization;

public class Main extends GenericsClazzMethodTypeBoundsSpecialization {

	public static void main(String[] args) {
		GenericsClazzMethodTypeBoundsSpecialization constr = new GenericsClazzMethodTypeBoundsSpecialization();
		constr.<Number>method1();
	}

	@Override
	public <T extends Number> void method1() {

	}
}
