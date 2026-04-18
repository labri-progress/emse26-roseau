package genericsWildcardsClazzMethodParamLowerBoundsSpecialization;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamLowerBoundsSpecialization.GenericsWildcardsClazzMethodParamLowerBoundsSpecialization;

public class Main extends GenericsWildcardsClazzMethodParamLowerBoundsSpecialization {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamLowerBoundsSpecialization constr = new GenericsWildcardsClazzMethodParamLowerBoundsSpecialization();
		ArrayList<Number> param1 = new ArrayList<Number>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<? super Number> param1) {

	}
}
